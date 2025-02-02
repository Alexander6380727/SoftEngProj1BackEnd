from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from database.models import User
import jwt

SECRET_KEY = "your_secret_key"

router = APIRouter()

class DashboardItem(BaseModel):
    name: str
    route: str
    icon: str

@router.get("/", response_model=list[DashboardItem])
async def get_dashboard_items(token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
        if role == "admin":
            return [
                {"name": "Inventory", "route": "/inventory", "icon": "box"},
                {"name": "Register User", "route": "/register", "icon": "user-plus"},
            ]
        elif role == "user":
            return [{"name": "Book Room", "route": "/book-room", "icon": "calendar"},
                    {"name": "Inventory", "route": "/inventory", "icon": "box"},]
        else:
            raise HTTPException(status_code=403, detail="Role not authorized")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")