from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.tamil_scraper import fetch_tamil_news_once
import logging
import os

logger = logging.getLogger("tamil_news_scheduler")

def job():
    db = SessionLocal()
    try:
        fetch_tamil_news_once(db)
    finally:
        db.close()

def start_scheduler():
    enable = os.getenv("ENABLE_SCHEDULER", "1") == "1"
    if not enable:
        logger.info("⏸️ Scheduler disabled via ENABLE_SCHEDULER=0")
        return
    try:
        minutes = int(os.getenv("SCHEDULE_MINUTES", "1"))
        if minutes < 1:
            minutes = 1
    except Exception:
        minutes = 1
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job,
        "interval",
        minutes=minutes,
        id="fetch_tamil_news",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(f"✅ Tamil News Scheduler started — running every {minutes} minute(s).")
