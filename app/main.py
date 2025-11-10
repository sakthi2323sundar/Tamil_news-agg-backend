from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, ensure_schema
from app import models  # Ensure models are registered before create_all
from app.api import news_routes, admin_routes
from app.scheduler import start_scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tamil_news_aggregator")

app = FastAPI(
    title="Tamil News Aggregator",
    version="0.1.0",
    description="Aggregates and summarizes Tamil news from multiple sources.",
)

# CORS for local file and any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(news_routes.router, prefix="/news", tags=["News"])
app.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "Welcome to Tamil News Aggregator API"}

@app.on_event("startup")
def startup_event():
    logger.info("🚀 Tamil News Aggregator starting... Initializing DB and scheduler.")
    try:
        ensure_schema()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created or verified.")
    except Exception as e:
        logger.error(f"⚠️ Failed to create/verify DB tables at startup: {e}")
    start_scheduler()
