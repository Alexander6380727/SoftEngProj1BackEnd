from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import json
import os

router = APIRouter()

# Load existing bookings from JSON file
if os.path.exists('bookings.json'):
    with open('bookings.json', 'r') as f:
        bookings = json.load(f)
else:
    bookings = []

class Booking(BaseModel):
    user_id: str  # Added to store the ID of the user who booked the room
    room_id: int  # Room ID for the booking
    booking_date: str  # Date of the booking
    booking_time: str  # Time of the booking
    purpose: str  # Purpose of the booking

@router.post("/book-room")
async def book_room(booking: Booking):
    print("Entering book_room function")  # Log entry into the function
    print("Incoming booking data:", booking)  # Log the incoming booking data

    # Check for existing bookings
    for b in bookings:
        if (b['room_id'] == booking.room_id and 
            b['booking_date'] == booking.booking_date and 
            b['booking_time'] == booking.booking_time):
            raise HTTPException(status_code=400, detail="Room is already booked for this time slot.")
    
    # If available, add the booking
    bookings.append(jsonable_encoder(booking))  # Add the new booking to the list
    with open('bookings.json', 'w') as f:
        json.dump(bookings, f)  # Save bookings to the JSON file
    return {"message": "Booking confirmed", "booking": booking}
