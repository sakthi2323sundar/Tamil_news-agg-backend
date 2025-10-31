from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.tamil_scraper import fetch_tamil_news_once

router = APIRouter()

@router.post("/fetch", summary="Manually trigger Tamil news fetch")
def fetch_news_now(db: Session = Depends(get_db)):
    count = fetch_tamil_news_once(db)
    return {"message": f"✅ {count} Tamil news articles fetched."}
