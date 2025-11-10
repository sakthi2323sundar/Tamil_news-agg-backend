from sqlalchemy.orm import Session
from app.models import News

def get_news(db: Session, limit: int = 20, source: str | None = None):
    """Fetch latest Tamil news from DB"""
    q = db.query(News)
    if source:
        q = q.filter(News.source == source)
    return (
        q.order_by(News.created_at.desc().nullslast(), News.id.desc())
         .limit(limit)
         .all()
    )
