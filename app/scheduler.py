from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.tamil_scraper import fetch_tamil_news_once
import logging

logger = logging.getLogger("tamil_news_scheduler")

def job():
    db = SessionLocal()
    try:
        fetch_tamil_news_once(db)
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", minutes=15, id="fetch_tamil_news")
    scheduler.start()
    logger.info("✅ Tamil News Scheduler started — running every 15 minutes.")
