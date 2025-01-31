from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

#DATABASE_URL = "postgresql+asyncpg://admin:adminpass@localhost:5432/labDB"
DATABASE_URL = "postgresql+asyncpg://admin:adminpass@localhost:5432/labdb"


engine = create_async_engine(DATABASE_URL, echo=True)
#async_session = sessionmaker(    engine, expire_on_commit=False, class_=AsyncSession)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# async def get_db():
#     async with async_session() as session:
#         yield session

async def get_db():
    async with SessionLocal() as session:
        yield session