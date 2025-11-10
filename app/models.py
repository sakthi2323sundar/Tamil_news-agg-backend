from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy import JSON
from datetime import datetime
from app.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100), nullable=False)
    summary = Column(Text, nullable=True)
    summaries = Column(JSON, nullable=True)
    summary_ta = Column(Text, nullable=True)
    summary_en = Column(Text, nullable=True)
    summary_hi = Column(Text, nullable=True)
    summary_kn = Column(Text, nullable=True)
    summary_ml = Column(Text, nullable=True)
    summary_te = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    language = Column(String(10), nullable=False, default="ta")
    published_at = Column(DateTime, nullable=True)
    scraped = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
