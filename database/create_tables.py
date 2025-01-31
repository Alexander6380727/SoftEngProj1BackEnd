from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# Replace 'DATABASE_URL' with your actual database URL
DATABASE_URL = "sqlite:///./test.db"  # Example for SQLite, change as needed

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

# Optional: Create a session to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
