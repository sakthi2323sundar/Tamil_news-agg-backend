from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.tamil_scraper import fetch_tamil_news_once, looks_tamil, translate_to_tamil, translate_text
from app.models import News
import time

router = APIRouter()

@router.post("/fetch", summary="Manually trigger Tamil news fetch")
def fetch_news_now(db: Session = Depends(get_db)):
    count = fetch_tamil_news_once(db)
    return {"message": f"✅ {count} Tamil news articles fetched."}

@router.post("/repair-summaries", summary="Translate any non-Tamil summaries to Tamil")
def repair_summaries(db: Session = Depends(get_db)):
    fixed = 0
    checked = 0
    items = db.query(News).all()
    for n in items:
        checked += 1
        current = (n.summary or "").strip()
        if current and looks_tamil(current):
            continue
        # Prefer translating summary; else use description
        source_text = current or (n.description or "")
        if not source_text:
            continue
        tx = translate_to_tamil(source_text)
        if tx and tx.strip():
            n.summary = tx.strip()
            fixed += 1
    if fixed:
        db.commit()
    return {"checked": checked, "fixed": fixed}


@router.post("/pretranslate", summary="Pre-translate latest items into multiple languages and cache in DB")
def pretranslate(
    langs: str = Query("hi,en,kn,ml,te", description="Comma-separated langs: ta,en,hi,kn,ml,te"),
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    SUPPORTED = {"ta", "en", "hi", "kn", "ml", "te"}
    targets = [l.strip().lower() for l in langs.split(",") if l.strip()]
    targets = [l for l in targets if l in SUPPORTED and l != "ta"]
    if not targets:
        return {"updated": 0, "message": "No valid target languages"}

    col_map = {
        "ta": "summary_ta",
        "en": "summary_en",
        "hi": "summary_hi",
        "kn": "summary_kn",
        "ml": "summary_ml",
        "te": "summary_te",
    }

    items = (
        db.query(News)
          .order_by(News.created_at.desc().nullslast(), News.id.desc())
          .limit(limit)
          .all()
    )
    updated = 0
    for n in items:
        src = (n.summary or n.description or n.title or "").strip()
        if not src:
            continue
        s = n.summaries or {}
        if not isinstance(s, dict):
            s = {}
        for lang in targets:
            if s.get(lang):
                continue
            tx = translate_text(src, lang)
            if not tx:
                time.sleep(1.2)
                tx = translate_text(src, lang)
            if tx:
                s[lang] = tx
                # also persist in dedicated language column if present
                try:
                    col = col_map.get(lang)
                    if col and getattr(n, col, None) != tx:
                        setattr(n, col, tx)
                except Exception:
                    pass
                updated += 1
            else:
                # hit rate limit; pause and continue to next item to spread load
                time.sleep(2.0)
        if s != (n.summaries or {}):
            n.summaries = s
            try:
                db.commit()
            except Exception:
                db.rollback()
                break
    return {"updated": updated, "count": len(items), "langs": targets}


@router.post("/backfill-columns", summary="Backfill per-language columns from existing summary and summaries JSON")
def backfill_columns(
    limit: int = Query(0, ge=0, description="0 means all"),
    db: Session = Depends(get_db),
):
    col_map = {
        "ta": "summary_ta",
        "en": "summary_en",
        "hi": "summary_hi",
        "kn": "summary_kn",
        "ml": "summary_ml",
        "te": "summary_te",
    }
    q = db.query(News).order_by(News.id.asc())
    if limit:
        items = q.limit(limit).all()
    else:
        items = q.all()
    updated = 0
    for n in items:
        changed = False
        ta_val = getattr(n, col_map["ta"], None)
        if (n.summary or "").strip() and not (ta_val or "").strip():
            setattr(n, col_map["ta"], n.summary.strip())
            changed = True
        s = n.summaries or {}
        if isinstance(s, dict):
            for lang, col in col_map.items():
                if lang == "ta":
                    continue
                val = s.get(lang)
                if val and not getattr(n, col, None):
                    setattr(n, col, val)
                    changed = True
        if changed:
            updated += 1
    if updated:
        try:
            db.commit()
        except Exception:
            db.rollback()
            return {"updated": 0}
    return {"updated": updated, "count": len(items)}
