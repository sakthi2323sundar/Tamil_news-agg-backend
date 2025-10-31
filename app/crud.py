from sqlalchemy.orm import Session
from app.models import News

def get_news(db: Session, limit: int = 20):
    """Fetch latest Tamil news from DB"""
    return db.query(News).order_by(News.published_at.desc().nullslast()).limit(limit).all()
