from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    if data.username == "admin" and data.password == "adminpass":
        return {"access_token": "admintoken123", "role": "admin"}
    elif data.username == "user" and data.password == "userpass":
        return {"access_token": "usertoken123", "role": "user"}
    elif data.username == "user2" and data.password == "userpass":
        return {"access_token": "usertoken223", "role": "user2"}
    raise HTTPException(status_code=401, detail="Invalid credentials")
