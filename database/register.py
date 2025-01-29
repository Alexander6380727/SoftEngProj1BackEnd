from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from database.models import User
from pydantic import BaseModel
import bcrypt

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str

@router.post("/")
async def register_user(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    hashed_password = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    new_user = User(username=data.username, password_hash=hashed_password, role=data.role)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "New account registered successfully"}
