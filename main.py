import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.authentication import router as auth_router
from database.register import router as register_router
from auth.dashboard import router as dashboard_router
from booking.booking import router as booking_router
from inventory import router as inventory_router
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import engine, get_db
from database.models import Base, User, Room
from passlib.context import CryptContext
from sqlalchemy.future import select
import bcrypt

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(register_router, prefix="/register", tags=["Register"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(booking_router, prefix="/api", tags=["Booking"])


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

async def seed_rooms(db: AsyncSession):
    # Check if any rooms already exist.
    existing_rooms_result = await db.execute(select(Room))  # Await query execution
    existing_rooms = existing_rooms_result.scalars().all()  # Extract scalar ORM results

    # If no existing rooms, add default rooms.
    if not existing_rooms:
        rooms = [
            Room(name="Room A"),
            Room(name="Room B"),
            Room(name="Room C"),
        ]
        db.add_all(rooms)
        await db.commit()  # Await commit for async operation


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drops existing schema
        await conn.run_sync(Base.metadata.create_all)  # Creates updated schema
    async with AsyncSession(engine) as session:
        await add_default_users(session)
        await seed_rooms(session)


async def add_default_users(db: AsyncSession):
    # Hash passwords for admin and user roles
    password_admin = bcrypt.hashpw("adminpass".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    password_user = bcrypt.hashpw("userpass".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Check if admin user exists
    admin_exists = await db.execute(select(User).where(User.username == "admin"))
    admin_row = admin_exists.scalar_one_or_none()

    # Check if standard user exists
    user_exists = await db.execute(select(User).where(User.username == "user"))
    user_row = user_exists.scalar_one_or_none()

    # Add admin user if not exists
    if not admin_row:
        admin = User(username="admin", password_hash=password_admin, role="admin")
        db.add(admin)

    # Add standard user if not exists
    if not user_row:
        user = User(username="user", password_hash=password_user, role="user")
        db.add(user)

    # Commit changes to the database
    await db.commit()

@app.on_event("startup")
async def on_startup():
    await init_db()