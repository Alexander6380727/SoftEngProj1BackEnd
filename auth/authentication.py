from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
#from database import get_db
from database.database import get_db
#from models import User
from database.models import User
from passlib.context import CryptContext
import jwt
import datetime
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your_secret_key"


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {
        "sub": user.username,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    access_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")

    return {"access_token": access_token, "role": user.role}
