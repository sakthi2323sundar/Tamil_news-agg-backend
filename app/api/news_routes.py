from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_news
from app.schemas import NewsResponse

router = APIRouter()

@router.get("/", response_model=list[NewsResponse], summary="Get latest Tamil news")
def fetch_news(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        news_list = get_news(db, limit=limit)
        return news_list or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
