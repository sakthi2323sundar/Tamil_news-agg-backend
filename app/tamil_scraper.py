import asyncio
import feedparser
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import News
import logging
import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ✅ Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger("tamil_scraper")

# Use a lighter default model to conserve quota; allow override via env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
# Track temporary quota lockout (epoch seconds); skip summarization until this time
_QUOTA_EXHAUSTED_UNTIL = 0.0

# ✅ Tamil news RSS feeds
RSS_FEEDS_ALL = {
    "BBC Tamil": ["https://feeds.bbci.co.uk/tamil/rss.xml"],
    "OneIndia Tamil": ["https://tamil.oneindia.com/rss/tamil-news-fb.xml"],
    "Dinamalar": [
        "https://www.dinamalar.com/rss/ta_tamil.asp",
        "https://www.dinamalar.com/rss.xml",
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
        "https://www.dinamani.com/rss/ta_tamil.xml",
    ],
}
RSS_FEEDS = RSS_FEEDS_ALL

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ta,en;q=0.8",
}

# Some sites aggressively block scraping; use RSS description only
SOURCE_FETCH_POLICY = {
    "OneIndia Tamil": {"rss_only": True},
    "BBC Tamil": {"rss_only": False},
    "Dinamalar": {"rss_only": True},
    "Vikatan": {"rss_only": True},
    "The Hindu Tamil": {"rss_only": True},
    "Dinamani": {"rss_only": True},
}


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
                # Always refresh summary if a new one is provided
                if item.get("summary") and item.get("summary") != (existing.summary or ""):
                    existing.summary = item.get("summary")
                    changed = True
                if not existing.description and item.get("description"):
                    existing.description = item.get("description")
                    changed = True
                if not existing.published_at and item.get("published_at"):
                    existing.published_at = item.get("published_at")
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
    if not text.strip() and not article_url:
        return ""

    now = time.time()
    if now < _QUOTA_EXHAUSTED_UNTIL:
        return ""

    client = genai.Client()

    def make_prompt(content: str, url: str | None) -> str:
        base = (
            "நீங்கள் ஒரு செய்தி தொகுப்பாளர். கீழே உள்ள கட்டுரையின் முக்கிய அம்சங்களை"
            " தமிழில் மட்டும் 3–4 வரிகளில், எளிய மற்றும் நடுநிலையான மொழியில் சுருக்கமாக எழுதுங்கள்."
            " தேதிகள், இடங்கள், எண்கள் போன்ற முக்கிய தகவல்களை மட்டும் வைத்துக் கொள்ளுங்கள்."
            " அத்தியாவசியமற்ற விபரங்களை தவிர்க்கவும்.\n\n"
        )
        if url:
            base += f"URL: {url}\n"
        if content:
            base += f"கட்டுரை:\n{content}"
        return base

    # Enable URL context and Google Search so the model can fetch the page if needed
    tools = [
        types.Tool(url_context=types.UrlContext()),
        types.Tool(google_search=types.GoogleSearch()),
    ]
    config = types.GenerateContentConfig(tools=tools)

    delays = [1, 3, 7]
    last_error = None
    for i, delay in enumerate(delays):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=make_prompt(text, article_url),
                config=config,
            )
            summary = response.text.strip() if response and hasattr(response, 'text') else ""
            if summary:
                return summary
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
        for entry in entries:
            article_url = entry.get("link", "")
            if not article_url or article_url in seen_urls:
                continue
            seen_urls.add(article_url)

            if policy.get("rss_only"):
                article_text = (entry.get("description") or "").strip()
            else:
                article_text = fetch_article_text(article_url) or (entry.get("description") or "").strip()

            summary = summarize_with_gemini(article_text, article_url) if (article_text or article_url) else ""
            if not summary:
                fallback = (entry.get("description") or "").strip()
                if fallback:
                    summary = (fallback[:400] + ("…" if len(fallback) > 400 else ""))

            all_news.append({
                "title": entry.get("title", ""),
                "description": entry.get("description", ""),
                "url": article_url,
                "source": source,
                "published_at": datetime.utcnow(),
                "summary": summary,
            })

    logger.info(f"✅ Scraped {len(all_news)} Tamil news items total.")
    if all_news:
        inserted = store_news_in_db(all_news, db)
        return inserted
    else:
        logger.warning("⚠️ No Tamil news items to insert.")
        return 0


if __name__ == "__main__":
    logger.info("🚀 Starting Tamil News Scraper manually...")
    db: Session = SessionLocal()
    inserted_count = fetch_tamil_news_once(db)
    logger.info(f"✅ Tamil news scraping completed successfully. Inserted {inserted_count} new articles.")
