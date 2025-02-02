from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable has been set")


engine = create_async_engine(DATABASE_URL, echo=True)
#async_session = sessionmaker(    engine, expire_on_commit=False, class_=AsyncSession)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# async def get_db():
#     async with async_session() as session:
#         yield session

async def get_db():
    async with SessionLocal() as session:
        yield session