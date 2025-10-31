from app.database import Base, engine
from app.models import News

print("⚙️ Dropping and recreating tables...")

# Drop old tables (⚠️ deletes all existing news)
Base.metadata.drop_all(bind=engine)

# Create new ones
Base.metadata.create_all(bind=engine)

print("✅ Database tables recreated successfully!")
