from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import get_db
from .models import Booking as BookingModel

router = APIRouter()

class Booking(BaseModel):
    user_id: str  # Added to store the ID of the user who booked the room
    room_id: int  # Room ID for the booking
    booking_date: str  # Date of the booking
    start_time: str  # Start time of the booking
    end_time: str  # End time of the booking
    purpose: str  # Purpose of the booking

@router.post("/book-room")
async def book_room(booking: Booking, db: Session = Depends(get_db)):
    print("Entering book_room function")  # Log entry into the function
    print("Incoming booking data:", booking)  # Log the incoming booking data

    # Check for existing bookings
    existing_bookings = db.query(BookingModel).filter(
        BookingModel.room_id == booking.room_id,
        BookingModel.booking_date == booking.booking_date,
        BookingModel.start_time == booking.start_time,
        BookingModel.end_time == booking.end_time
    ).all()

    if existing_bookings:
        raise HTTPException(status_code=400, detail="Room is already booked for this time slot.")
    
    # If available, add the booking
    new_booking = BookingModel(
        user_id=booking.user_id,
        room_id=booking.room_id,
        booking_date=booking.booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        purpose=booking.purpose
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return {"message": "Booking confirmed", "booking": new_booking}

@router.get("/user-bookings/{user_id}")
async def get_user_bookings(user_id: str, db: Session = Depends(get_db)):
    bookings = db.query(BookingModel).filter(BookingModel.user_id == user_id).all()
    return {"bookings": bookings}
