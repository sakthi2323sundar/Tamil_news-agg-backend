from datetime import datetime
from pydantic import BaseModel

class NewsResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    url: str
    source: str
    summary: str | None = None
    language: str
    published_at: datetime | None = None
    created_at: datetime

    class Config:
        orm_mode = True
