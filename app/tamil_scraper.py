import asyncio
import feedparser
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import News
import logging
import os
import time
import requests
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import html as _html
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # type: ignore
# Gemini SDK is optional; handle import issues gracefully
try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
    _GENAI_AVAILABLE = True
except Exception as _e:
    logging.getLogger("tamil_scraper").warning(f"Gemini SDK not available, summaries will be skipped: {_e}")
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator as _DTGoogleTranslator  # type: ignore
    _DEEP_AVAILABLE = True
except Exception:
    _DTGoogleTranslator = None  # type: ignore
    _DEEP_AVAILABLE = False

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger("tamil_scraper")

# Use Gemini 2.5 Flash by default; can override via env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Default OFF to avoid pulling English context; opt-in via env
ENABLE_URL_CONTEXT = os.getenv("ENABLE_URL_CONTEXT", "0") == "1"
ENABLE_GOOGLE_SEARCH = os.getenv("ENABLE_GOOGLE_SEARCH", "0") == "1"
MAX_ENTRY_AGE_HOURS = int(os.getenv("MAX_ENTRY_AGE_HOURS", "48"))
# If GEMINI_API_KEY is provided but GOOGLE_API_KEY is not, set it for the SDK
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY") or ""
# Track temporary quota lockout (epoch seconds); skip summarization until this time
_QUOTA_EXHAUSTED_UNTIL = 0.0

# ✅ All RSS Feeds (Tamil News)
RSS_FEEDS_ALL = {
    "BBC Tamil": [
        "https://feeds.bbci.co.uk/tamil/rss.xml",
        "http://www.bbc.co.uk/tamil/index.xml",
    ],
    "OneIndia Tamil": [
        "https://tamil.oneindia.com/rss/tamil-news-fb.xml"
    ],
    "News18 Tamil": [
        "https://tamil.news18.com/commonfeeds/v1/tam/rss/live-updates.xml"
    ],
    "News18 Coimbatore": [
        "https://tamil.news18.com/commonfeeds/v1/tam/rss/coimbatore-district.xml"
    ],
    "Dinamalar": [
        "https://www.dinamalar.com/rss/ta_tamil.asp"
    ],
    "Vikatan": [
        "https://www.vikatan.com/rss/tn",
        "https://www.vikatan.com/rss/india",
        "https://www.vikatan.com/rss/world",
    ],
    "The Hindu Tamil": [
        "https://www.hindutamil.in/rss/tamilnadu.xml",
        "https://www.hindutamil.in/rss/india.xml",
        "https://www.hindutamil.in/rss/world.xml",
        "https://www.hindutamil.in/rss/cinema.xml",
        "https://www.hindutamil.in/rss/sports.xml",
    ],
    "Dinamani": [
        "https://www.dinamani.com/rss/ta_tamil.xml"
    ],

    # ✅ Added More Trusted Tamil Feeds
    "Thanthi TV Tamil": [
        "https://www.dailythanthi.com/rssfeed"
    ],
    "Puthiyathalaimurai": [
        "https://www.puthiyathalaimurai.com/rss/ta/news"
    ],
    "Polimer News": [
        "https://www.polimernews.com/rss/tamilnadu"
    ],
    "News7 Tamil": [
        "https://www.news7tamil.live/rss"
    ],
    "Hindustan Times Tamil": [
        "https://tamil.hindustantimes.com/rss"
    ],
}
# Limit to working sources first; expand gradually after verifying others
RSS_FEEDS = {
    "BBC Tamil": RSS_FEEDS_ALL["BBC Tamil"],
    "OneIndia Tamil": RSS_FEEDS_ALL["OneIndia Tamil"],
    "News18 Tamil": RSS_FEEDS_ALL["News18 Tamil"],
    "News18 Coimbatore": RSS_FEEDS_ALL["News18 Coimbatore"],
    "Dinamalar": RSS_FEEDS_ALL["Dinamalar"],
    "Vikatan": RSS_FEEDS_ALL["Vikatan"],
    "The Hindu Tamil": RSS_FEEDS_ALL["The Hindu Tamil"],
    "Dinamani": RSS_FEEDS_ALL["Dinamani"],
    "Thanthi TV Tamil": RSS_FEEDS_ALL["Thanthi TV Tamil"],
    "Puthiyathalaimurai": RSS_FEEDS_ALL["Puthiyathalaimurai"],
    "Polimer News": RSS_FEEDS_ALL["Polimer News"],
    "News7 Tamil": RSS_FEEDS_ALL["News7 Tamil"],
    "Hindustan Times Tamil": RSS_FEEDS_ALL["Hindustan Times Tamil"],
}


# In-memory tracker for last seen published time per feed URL (epoch seconds)
LAST_PUBDATE: dict[str, float] = {}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ta,en;q=0.8",
}

# Some sites aggressively block scraping; use RSS description only
SOURCE_FETCH_POLICY = {
    "OneIndia Tamil": {"rss_only": True},
    "BBC Tamil": {"rss_only": False},
    "News18 Tamil": {"rss_only": True},
    "News18 Coimbatore": {"rss_only": True},
    "Dinamalar": {"rss_only": True},
    "Vikatan": {"rss_only": True},
    "The Hindu Tamil": {"rss_only": True},
    "Dinamani": {"rss_only": True},
    "Thanthi TV Tamil": {"rss_only": True},
    "Puthiyathalaimurai": {"rss_only": True},
    "Polimer News": {"rss_only": True},
    "News7 Tamil": {"rss_only": True},
    "Hindustan Times Tamil": {"rss_only": True},
}

# Sources for which English summaries are allowed (no forced Tamil enforcement)
ALLOW_ENGLISH_SOURCES = set()


def extract_image_from_entry(entry):
    try:
        media = entry.get('media_content') or entry.get('media_thumbnail')
        if isinstance(media, list) and media:
            url = media[0].get('url') or media[0].get('href')
            if url:
                return url
        if isinstance(media, dict):
            url = media.get('url') or media.get('href')
            if url:
                return url
    except Exception:
        pass
    enclosure = entry.get('enclosures') or entry.get('enclosure')
    if isinstance(enclosure, list) and enclosure:
        href = enclosure[0].get('href') or enclosure[0].get('url')
        if href:
            return href
    if isinstance(enclosure, dict):
        href = enclosure.get('href') or enclosure.get('url')
        if href:
            return href
    html_source = None
    if entry.get('content') and isinstance(entry['content'], list) and entry['content']:
        html_source = entry['content'][0].get('value')
    elif entry.get('summary_detail') and entry['summary_detail'].get('value'):
        html_source = entry['summary_detail']['value']
    elif entry.get('summary'):
        html_source = entry.get('summary')
    if html_source:
        try:
            soup = BeautifulSoup(html_source, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img.get('src')
        except Exception:
            pass
    return None


def extract_entry_link(entry):
    # Prefer standard 'link'
    link = entry.get("link")
    if link:
        return str(link).strip()
    # Some feeds provide a list of link objects
    links = entry.get("links")
    if isinstance(links, list) and links:
        first = links[0]
        if isinstance(first, dict):
            href = first.get("href") or first.get("url")
            if href:
                return str(href).strip()
        elif isinstance(first, str) and first:
            return first.strip()
    # Fallbacks commonly used in RSS/Atom
    for k in ("id", "guid", "url", "href"):
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            href = v.get("href") or v.get("url")
            if href:
                return str(href).strip()
    return ""


def looks_tamil(text: str) -> bool:
    try:
        # Heuristic: ensure sufficient Tamil chars and low Latin ratio
        ta = sum(1 for ch in text if '\u0b80' <= ch <= '\u0bff')
        non_ws = sum(1 for ch in text if not ch.isspace())
        latin = sum(1 for ch in text if ('A' <= ch <= 'Z') or ('a' <= ch <= 'z'))
        if non_ws == 0:
            return False
        return ta >= max(5, int(0.25 * non_ws)) and latin <= int(0.15 * non_ws)
    except Exception:
        return False


def translate_to_tamil(text: str) -> str:
    if not _GENAI_AVAILABLE:
        return ""
    try:
        client = genai.Client()
        prompt = (
            "கீழேயுள்ள உரையை தமிழில் மட்டும் இயல்பாக மாற்றி எழுதி வழங்கவும்."
            " எந்த ஆங்கில சொற்களும் அல்லது விளக்கங்களும் சேர்க்காதீர்கள்;"
            " மொழிபெயர்க்கப்பட்ட தமிழ் உரை மட்டும் திருப்பவும்.\n\n"
            f"உரை:\n{text}"
        )
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        out = resp.text.strip() if resp and hasattr(resp, 'text') else ""
        return out
    except Exception:
        return ""


def translate_text(text: str, target_lang: str) -> str:
    """Translate arbitrary text to the target language code.
    Supported: ta (Tamil), en (English), hi (Hindi), kn (Kannada), ml (Malayalam), te (Telugu)
    Returns empty string on failure.
    """
    target_lang = (target_lang or "").lower().strip()
    lang_map = {
        "ta": "Tamil",
        "en": "English",
        "hi": "Hindi",
        "kn": "Kannada",
        "ml": "Malayalam",
        "te": "Telugu",
    }
    if target_lang not in lang_map:
        return ""
    if _DEEP_AVAILABLE:
        try:
            out = _DTGoogleTranslator(source='auto', target=target_lang).translate(text)
            if isinstance(out, str) and out.strip():
                return out.strip()
        except Exception:
            pass
    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()
    if api_key:
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            payload = {
                "q": text,
                "target": target_lang,
                "format": "text",
                "model": "nmt",
                "key": api_key,
            }
            r = requests.post(url, data=payload, timeout=10)
            if r.ok:
                j = r.json()
                tr_list = ((j or {}).get("data") or {}).get("translations") or []
                if tr_list:
                    out = tr_list[0].get("translatedText") or ""
                    return _html.unescape(out).strip()
        except Exception:
            pass
    if not _GENAI_AVAILABLE:
        return ""
    try:
        client = genai.Client()
        prompt = (
            f"Translate the following text into {lang_map[target_lang]} only. "
            f"Return strictly plain {lang_map[target_lang]} with no extra notes, labels, or explanations.\n\n"
            f"Text:\n{text}"
        )
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        out = resp.text.strip() if resp and hasattr(resp, 'text') else ""
        return out
    except Exception:
        return ""

def filter_to_tamil(text: str) -> str:
    """Best-effort: keep Tamil letters, whitespace, digits and common punctuation.
    This is a last-resort fallback to avoid showing English when translation is unavailable."""
    try:
        allowed = []
        for ch in text:
            if ('\u0b80' <= ch <= '\u0bff') or ch.isdigit() or ch.isspace() or ch in ",.;:!?()[]{}-–—…'\"/|&%+@#“”‘’":
                allowed.append(ch)
        out = ''.join(allowed)
        return out.strip()
    except Exception:
        return ""


def extract_image_from_article(url):
    try:
        headers = dict(DEFAULT_HEADERS)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Prefer OpenGraph image
        og = soup.find('meta', attrs={'property': 'og:image'})
        if og and og.get('content'):
            return og.get('content')
        tw = soup.find('meta', attrs={'name': 'twitter:image'})
        if tw and tw.get('content'):
            return tw.get('content')
        # Fallback first <img>
        img = soup.find('img')
        if img and img.get('src'):
            return img.get('src')
    except Exception as e:
        logger.debug(f"Image extract failed for {url}: {e}")
    return None


def fetch_rss_feed(url):
    """Fetch RSS feed and return parsed entries"""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        ct = resp.headers.get("Content-Type", "")
        if not resp.ok:
            logger.warning(f"⚠️ RSS HTTP {resp.status_code} for {url} ({ct})")
        data = resp.content if resp.ok else b""
        feed = feedparser.parse(data or url)
        if not feed.entries:
            logger.warning(f"⚠️ No entries found for {url} (content-type: {ct})")
        return feed.entries or []
    except Exception as e:
        logger.error(f"❌ Error fetching {url}: {e}")
        return []


def store_news_in_db(news_items, db: Session):
    """Insert/update Tamil news items into PostgreSQL database"""
    upserted_count = 0
    try:
        for item in news_items:
            existing = db.query(News).filter(News.url == item["url"]).first()
            if existing:
                changed = False
                # Refresh summary if a new non-empty one is provided OR
                # if the existing summary is non-Tamil (allow clearing to empty)
                new_sum = item.get("summary", "")
                old_sum = existing.summary or ""
                if (new_sum != old_sum) and (new_sum or (old_sum and not looks_tamil(old_sum))):
                    existing.summary = new_sum
                    try:
                        # Keep dedicated Tamil column in sync
                        existing.summary_ta = new_sum or existing.summary_ta
                    except Exception:
                        pass
                    changed = True
                # Ensure summaries JSON has Tamil copy
                try:
                    if new_sum:
                        s = existing.summaries or {}
                        if not isinstance(s, dict):
                            s = {}
                        if s.get("ta") != new_sum:
                            s["ta"] = new_sum
                            existing.summaries = s
                            try:
                                existing.summary_ta = new_sum
                            except Exception:
                                pass
                            changed = True
                except Exception:
                    pass
                if not existing.description and item.get("description"):
                    existing.description = item.get("description")
                    changed = True
                if not existing.published_at and item.get("published_at"):
                    existing.published_at = item.get("published_at")
                    changed = True
                if not existing.image_url and item.get("image_url"):
                    existing.image_url = item.get("image_url")
                    changed = True
                if changed:
                    upserted_count += 1
                continue

                
            db.add(News(
                title=item["title"],
                description=item["description"],
                url=item["url"],
                source=item["source"],
                summary=item.get("summary", ""),
                summaries={"ta": item.get("summary", "")} if item.get("summary") else None,
                summary_ta=item.get("summary", "") or None,
                image_url=item.get("image_url"),
                language="ta",
                published_at=item.get("published_at", datetime.utcnow()),
            ))
            upserted_count += 1

        db.commit()
        logger.info(f"✅ Upserted {upserted_count} Tamil news articles (new or updated).")
        return upserted_count
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Database insert failed: {e}")
        return 0
    finally:
        # Let FastAPI dependency close the session
        pass


def fetch_article_text(url):
    try:
        # Add Referer header to reduce 403s
        headers = dict(DEFAULT_HEADERS)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            pass
        resp = requests.get(url, timeout=12, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = soup.find_all('p')
        article_text = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs])
        # Trim and cap length to control token usage
        article_text = article_text.strip()[:6000]
        return article_text
    except Exception as e:
        logger.warning(f"Failed to fetch article from {url}: {e}")
        return ""


def summarize_with_gemini(text: str, article_url: str | None = None) -> str:
    global _QUOTA_EXHAUSTED_UNTIL
    if os.getenv("SKIP_SUMMARY", "0") == "1":
        return ""
    if not text.strip() and not article_url:
        return ""
    if not _GENAI_AVAILABLE:
        return ""

    now = time.time()
    if now < _QUOTA_EXHAUSTED_UNTIL:
        return ""

    client = genai.Client()

    def make_prompt(content: str, url: str | None) -> str:
        base = (
            "நீங்கள் ஒரு செய்தி தொகுப்பாளர். கீழேயுள்ள உள்ளடக்கத்தை"
            " தமிழில் மட்டும் 4-5 வாக்கியங்களாக, இயல்பான உரை வடிவில் (புள்ளிகள் இல்லாமல்) சுருக்கமாக எழுதுங்கள்."
            " தேதிகள், இடங்கள், எண்கள் போன்ற முக்கிய விவரங்களை விடாமல் சேர்க்கவும்."
            " முக்கியம்: பதில் 100% தமிழில் மட்டும் இருக்க வேண்டும்; ஆங்கில சொற்கள்/இணைமொழி பயன்படுத்தாதீர்கள்."
            " உள்ளடக்கம் ஆங்கிலத்தில் இருந்தாலும் தமிழில் மொழிபெயர்த்து சுருக்கம் எழுதவும்.\n\n"
        )
        if url:
            base += f"URL: {url}\n"
        if content:
            base += f"கட்டுரை:\n{content}"
        return base

    tools: list[types.Tool] = []
    if ENABLE_URL_CONTEXT:
        tools.append(types.Tool(url_context=types.UrlContext()))
    if ENABLE_GOOGLE_SEARCH:
        # Use supported google_search tool; google_search_retrieval is no longer accepted
        try:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        except Exception as e:
            logger.warning(f"google_search tool unavailable or unsupported in current SDK: {e}")

    config = types.GenerateContentConfig(tools=tools) if tools else None

    delays = [1, 3, 7]
    last_error = None
    for i, delay in enumerate(delays):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=make_prompt(text, article_url),
                **({"config": config} if config else {})
            )
            summary = response.text.strip() if response and hasattr(response, 'text') else ""
            # If model returns non-Tamil, try translating summary; if still not, translate original content
            if summary and not looks_tamil(summary):
                tx = translate_to_tamil(summary)
                if tx and looks_tamil(tx):
                    summary = tx
                else:
                    src_txt = (article_text or (entry.get("description") or "")).strip()
                    if src_txt:
                        tx2 = translate_to_tamil(src_txt)
                        if tx2 and looks_tamil(tx2):
                            summary = tx2
                        else:
                            filtered = filter_to_tamil(summary or src_txt)
                            if filtered:
                                summary = filtered
                            elif source in FORCE_TRANSLATE_SOURCES:
                                fb = (entry.get("description") or "").strip()
                                if fb:
                                    summary = (fb[:400] + ("…" if len(fb) > 400 else ""))
                            else:
                                summary = ""
        except Exception as e:
            last_error = e
            msg = str(e)
            logger.warning(f"Gemini summarization attempt {i+1} failed: {e}")
            if "RESOURCE_EXHAUSTED" in msg or "Too Many Requests" in msg or "429" in msg:
                import re
                m = re.search(r"retryDelay['\"]?:\s*'?(\d+)(?:\.\d+)?s", msg)
                wait_s = int(m.group(1)) if m else 60
                _QUOTA_EXHAUSTED_UNTIL = time.time() + wait_s
                logger.warning(f"Quota exhausted. Pausing summarization for ~{wait_s}s.")
                return ""
        time.sleep(delay)

    logger.warning(f"Gemini summarization failed after retries: {last_error}")
    return ""


def fetch_tamil_news_once(db):
    """Fetch Tamil news from multiple sources"""
    all_news = []
    seen_urls = set()
    for source, url_list in RSS_FEEDS.items():
        logger.info(f"📰 Fetching from {source}")
        entries = []
        for candidate_url in url_list:
            entries = fetch_rss_feed(candidate_url)
            if entries:
                break
        logger.info(f"✅ Found {len(entries)} entries in {source}")
        policy = SOURCE_FETCH_POLICY.get(source, {"rss_only": False})
        # Optional: skip entries already seen for this feed URL using published timestamp
        filtered = []
        try:
            last_seen = None
            # Use the specific URL we fetched from for tracking if available
            track_url = candidate_url if entries else None
            if track_url:
                last_seen = LAST_PUBDATE.get(track_url)
            newest_ts = last_seen or 0.0
            for entry in entries:
                ts = None
                parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if parsed:
                    import time as _time
                    ts = float(_time.mktime(parsed))
                if last_seen is not None and ts is not None and ts <= last_seen:
                    continue
                if ts is not None and ts > newest_ts:
                    newest_ts = ts
                filtered.append(entry)
            if track_url and newest_ts and newest_ts != (last_seen or 0.0):
                LAST_PUBDATE[track_url] = newest_ts
        except Exception:
            filtered = entries
        for entry in (filtered or entries):
            article_url = extract_entry_link(entry)
            if not article_url or article_url in seen_urls:
                continue
            seen_urls.add(article_url)

            if policy.get("rss_only"):
                article_text = (entry.get("description") or "").strip()
            else:
                article_text = fetch_article_text(article_url) or (entry.get("description") or "").strip()

            # Image selection: RSS first, then article
            image_url = extract_image_from_entry(entry) or extract_image_from_article(article_url)

            summary = summarize_with_gemini(article_text, article_url) if (article_text or article_url) else ""
            if not summary:
                fallback = (entry.get("description") or "").strip()
                if fallback:
                    summary = (fallback[:400] + ("…" if len(fallback) > 400 else ""))
            # For sources where English is acceptable, skip Tamil-only coercion
            enforce_tamil = source not in ALLOW_ENGLISH_SOURCES

            # Determine published_at with proper timezone handling to match source site
            try:
                from datetime import timezone as _tz
                pub_dt = None

                # 1) Try parsing RFC822/ISO-like date strings with timezone
                date_str = (
                    entry.get("published")
                    or entry.get("updated")
                    or entry.get("dc:date")
                    or entry.get("pubDate")
                )
                if isinstance(date_str, str) and date_str.strip():
                    try:
                        dt = parsedate_to_datetime(date_str.strip())
                        if dt is not None:
                            if dt.tzinfo is None:
                                # No timezone in string. Assume IST to match Tamil sites.
                                if ZoneInfo is not None:
                                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
                                else:
                                    # Fallback: treat as UTC if zoneinfo unavailable
                                    dt = dt.replace(tzinfo=_tz.utc)
                            # Convert to UTC for storage
                            pub_dt = dt.astimezone(_tz.utc)
                    except Exception:
                        pass

                # 2) Fallback to feedparser's struct_time
                if pub_dt is None:
                    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published_parsed:
                        try:
                            import calendar as _cal
                            ts = _cal.timegm(published_parsed)  # treat as UTC epoch
                            pub_dt = datetime.fromtimestamp(ts, tz=_tz.utc)
                        except Exception:
                            pass

                # 3) Ultimate fallback: current UTC
                if pub_dt is None:
                    pub_dt = datetime.now(_tz.utc)
            except Exception:
                from datetime import timezone as _tz
                pub_dt = datetime.now(_tz.utc)

            # Skip very old entries based on MAX_ENTRY_AGE_HOURS
            try:
                from datetime import timezone as _tz
                cutoff = datetime.now(_tz.utc) - timedelta(hours=MAX_ENTRY_AGE_HOURS)
                if pub_dt < cutoff:
                    continue
            except Exception:
                pass

            all_news.append({
                "title": entry.get("title", ""),
                "description": entry.get("description", ""),
                "url": article_url,
                "source": source,
                "published_at": pub_dt,
                "summary": summary,
                "image_url": image_url,
            })

    logger.info(f"✅ Scraped {len(all_news)} Tamil news items total.")
    if all_news:
        inserted = store_news_in_db(all_news, db)
        return inserted
    else:
        logger.warning("⚠️ No Tamil news items to insert.")
        return 0


def backfill_goodreturns_summaries(db: Session, batch_size: int = 200) -> int:
    updated = 0
    try:
        q = db.query(News).filter(News.source == "GoodReturns Tamil")
        for item in q.yield_per(batch_size):
            try:
                text = (item.summary or "").strip()
                if not text:
                    text = (item.description or "").strip()
                if not text:
                    continue
                if looks_tamil(text):
                    continue
                tx = translate_to_tamil(text)
                if tx and looks_tamil(tx):
                    item.summary = tx
                    updated += 1
                else:
                    filtered = filter_to_tamil(text)
                    if filtered:
                        item.summary = filtered
                        updated += 1
            except Exception:
                continue
        if updated:
            db.commit()
        return updated
    except Exception:
        db.rollback()
        return updated


def purge_goodreturns(db: Session) -> int:
    try:
        q = db.query(News).filter(News.source == "GoodReturns Tamil")
        count = q.count()
        if count:
            q.delete(synchronize_session=False)
            db.commit()
        return count
    except Exception:
        db.rollback()
        return 0

if __name__ == "__main__":
    logger.info("🚀 Starting Tamil News Scraper manually...")
    db: Session = SessionLocal()
    import os as _os
    if _os.getenv("PURGE_GOODRETURNS", "0") == "1":
        cnt = purge_goodreturns(db)
        logger.info(f"✅ Purged GoodReturns Tamil records: {cnt} items deleted.")
    elif _os.getenv("BACKFILL_GOODRETURNS", "0") == "1":
        cnt = backfill_goodreturns_summaries(db)
        logger.info(f"✅ Backfilled GoodReturns Tamil summaries: {cnt} items updated.")
    else:
        inserted_count = fetch_tamil_news_once(db)
        logger.info(f"✅ Tamil news scraping completed successfully. Inserted {inserted_count} new articles.")
