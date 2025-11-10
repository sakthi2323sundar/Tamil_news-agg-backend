import logging
from datetime import timezone
from typing import Optional

from app.database import SessionLocal
from app.models import News

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger("normalize_timestamps")

def make_utc(dt) -> Optional[object]:
    if dt is None:
        return None
    try:
        if getattr(dt, "tzinfo", None) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return dt

def main():
    db = SessionLocal()
    updated = 0
    try:
        items = db.query(News).all()
        for n in items:
            orig_pub = n.published_at
            orig_created = n.created_at

            # Normalize created_at first
            if getattr(n, "created_at", None) is not None:
                n.created_at = make_utc(n.created_at)

            # Normalize published_at; backfill if missing
            if getattr(n, "published_at", None) is None:
                n.published_at = n.created_at or None
            else:
                n.published_at = make_utc(n.published_at)

            if n.published_at != orig_pub or n.created_at != orig_created:
                updated += 1
        db.commit()
        logger.info(f"✅ Normalization complete. Rows updated: {updated}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to normalize timestamps: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
