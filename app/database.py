from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger("app.database")

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URI") or ""
DATABASE_URL = DATABASE_URL.strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL.split("://",1)[0]:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=(
        {"connect_timeout": 5} if DATABASE_URL.startswith("postgresql+") else (
            {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        )
    ),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_schema():
    """Ensure new columns exist without a full migration tool.
    - Adds news.summaries if it does not exist.
    - Adds per-language summary columns if they do not exist: summary_ta, summary_en, summary_hi, summary_kn, summary_ml, summary_te.
    """
    try:
        backend = engine.url.get_backend_name()
        with engine.begin() as conn:
            if backend.startswith("postgresql"):
                conn.exec_driver_sql(
                    """
                    ALTER TABLE news
                    ADD COLUMN IF NOT EXISTS summaries JSONB;
                    """
                )
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_ta TEXT;")
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_en TEXT;")
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_hi TEXT;")
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_kn TEXT;")
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_ml TEXT;")
                conn.exec_driver_sql("ALTER TABLE news ADD COLUMN IF NOT EXISTS summary_te TEXT;")
            elif backend.startswith("sqlite"):
                # SQLite lacks IF NOT EXISTS for ADD COLUMN in older versions; try and ignore error
                try:
                    conn.exec_driver_sql("ALTER TABLE news ADD COLUMN summaries TEXT")
                except Exception:
                    pass
                for col in ("summary_ta", "summary_en", "summary_hi", "summary_kn", "summary_ml", "summary_te"):
                    try:
                        conn.exec_driver_sql(f"ALTER TABLE news ADD COLUMN {col} TEXT")
                    except Exception:
                        pass
    except Exception as e:
        logger = logging.getLogger("app.database")
        logger.warning(f"ensure_schema skipped or failed: {e}")
