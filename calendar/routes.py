from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

router = APIRouter()

class Event(BaseModel):
    id: int
    title: str
    date: str

@router.get("/events", response_model=List[Event])
async def get_events():
    return [
        {"id": 1, "title": "Admin Meeting", "date": "2025-01-22"},
        {"id": 2, "title": "User Workshop", "date": "2025-01-23"},
    ]
