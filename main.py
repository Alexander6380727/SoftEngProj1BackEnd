import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.authentication import router as auth_router
from database.register import router as register_router
from auth.dashboard import router as dashboard_router
from database.database import engine
from database.models import Base

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(register_router, prefix="/register", tags=["Register"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI backend"}

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drops existing schema
        await conn.run_sync(Base.metadata.create_all)  # Creates updated schema

@app.on_event("startup")
async def on_startup():
    await init_db()