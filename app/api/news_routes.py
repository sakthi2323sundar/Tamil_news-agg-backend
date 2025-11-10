from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_news
from app.schemas import NewsResponse
from app.models import News
from datetime import timezone
from app.tamil_scraper import translate_text
import time

# Simple in-memory LRU-ish cache for translated summaries
_TX_CACHE: dict[tuple[int, str], str] = {}
_TX_ORDER: list[tuple[int, str]] = []
_TX_MAX = 2000

def _cache_get(key: tuple[int, str]) -> str | None:
    try:
        return _TX_CACHE.get(key)
    except Exception:
        return None

def _cache_set(key: tuple[int, str], value: str) -> None:
    try:
        if key in _TX_CACHE:
            _TX_CACHE[key] = value
            try:
                _TX_ORDER.remove(key)
            except Exception:
                pass
            _TX_ORDER.append(key)
        else:
            _TX_CACHE[key] = value
            _TX_ORDER.append(key)
            if len(_TX_ORDER) > _TX_MAX:
                old = _TX_ORDER.pop(0)
                _TX_CACHE.pop(old, None)
    except Exception:
        pass

router = APIRouter()

@router.get("/", response_model=list[NewsResponse], summary="Get latest Tamil news")
def fetch_news(
    limit: int = Query(50, ge=1, le=200),
    source: str | None = Query(None, description="Filter by source name"),
    lang: str = Query("ta", description="Response summary language: ta|en|hi|kn|ml|te"),
    db: Session = Depends(get_db),
):
    try:
        SUPPORTED = {"ta", "en", "hi", "kn", "ml", "te"}
        lang = (lang or "ta").lower()
        if lang not in SUPPORTED:
            lang = "ta"

        # map language code to News column attribute
        col_map = {
            "ta": "summary_ta",
            "en": "summary_en",
            "hi": "summary_hi",
            "kn": "summary_kn",
            "ml": "summary_ml",
            "te": "summary_te",
        }

        news_list = get_news(db, limit=limit, source=source) or []
        # Ensure timezone-aware UTC datetimes so clients compute relative time correctly
        # Per-request translation cap to reduce 429s
        max_tx = 30
        tx_count = 0
        dirty = False
        for n in news_list:
            if getattr(n, "published_at", None) and n.published_at.tzinfo is None:
                n.published_at = n.published_at.replace(tzinfo=timezone.utc)
            if getattr(n, "created_at", None) and n.created_at.tzinfo is None:
                n.created_at = n.created_at.replace(tzinfo=timezone.utc)
            # On-the-fly translation of summary for requested language
            if lang == "ta":
                # Prefer dedicated column if available
                try:
                    col = col_map.get("ta")
                    if col:
                        ta_val = getattr(n, col, None)
                        if ta_val:
                            n.summary = ta_val
                            try:
                                n.language = "ta"
                            except Exception:
                                pass
                except Exception:
                    pass
            else:
                key = (getattr(n, "id", 0) or 0, lang)
                cached = _cache_get(key)
                if cached:
                    n.summary = cached
                    try:
                        n.language = lang
                    except Exception:
                        pass
                else:
                    # 1) Check dedicated per-language column first
                    try:
                        col = col_map.get(lang)
                        if col:
                            col_val = getattr(n, col, None)
                            if col_val:
                                n.summary = col_val
                                _cache_set(key, n.summary or "")
                                try:
                                    n.language = lang
                                except Exception:
                                    pass
                                continue
                    except Exception:
                        pass
                    # 2) Then check summaries JSON
                    try:
                        s = getattr(n, "summaries", None)
                        if isinstance(s, dict) and s.get(lang):
                            n.summary = s.get(lang) or n.summary
                            _cache_set(key, n.summary or "")
                            try:
                                n.language = lang
                            except Exception:
                                pass
                            continue
                    except Exception:
                        pass
                    if tx_count >= max_tx:
                        continue
                    src = (n.summary or n.description or n.title or "").strip()
                    if not src:
                        continue
                    # try translate once, then retry once after short backoff if empty (likely 429)
                    tx = translate_text(src, lang)
                    if not tx:
                        time.sleep(1.2)
                        tx = translate_text(src, lang)
                    if tx:
                        n.summary = tx
                        _cache_set(key, tx)
                        tx_count += 1
                        # persist into DB summaries for caching
                        try:
                            s = getattr(n, "summaries", None) or {}
                            if not isinstance(s, dict):
                                s = {}
                            if s.get(lang) != tx:
                                s[lang] = tx
                                n.summaries = s
                                dirty = True
                        except Exception:
                            pass
                        # persist into dedicated per-language column
                        try:
                            col = col_map.get(lang)
                            if col and getattr(n, col, None) != tx:
                                setattr(n, col, tx)
                                dirty = True
                        except Exception:
                            pass
                        try:
                            n.language = lang
                        except Exception:
                            pass
                    else:
                        # Likely rate-limited for this item; continue with others
                        continue
        if dirty:
            try:
                db.commit()
            except Exception:
                pass
        return news_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
