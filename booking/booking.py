from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, time, datetime
from database.database import get_db
from database.models import Room, Booking as BookingModel
import jwt
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.sql import text
from database.models import User
from fastapi import status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter()

SECRET_KEY = "your_secret_key"


class Booking(BaseModel):
    user_id: int  # Added to store the ID of the user who booked the room
    room_id: int  # Room ID for the booking
    booking_date: date  # Pydantic will automatically validate date format (YYYY-MM-DD)
    start_time: time  # Pydantic will validate time format (HH:MM)
    end_time: time  # End time of the booking (HH:MM)
    purpose: str  # Purpose of the booking

@router.get("/user-bookings")
async def get_user_bookings(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    Endpoint to fetch all bookings for the authenticated user using the token.
    """
    try:
        # Decode the JWT token to extract the user ID
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        token_user_id = payload.get("sub")  # Extract the user ID (subject) from the token

        if not token_user_id:
            raise HTTPException(
                status_code=401, detail="Invalid token: user ID not found"
            )

        # Fetch all bookings for the user identified by the token
        result = await db.execute(
            select(BookingModel).where(
                BookingModel.user_id == int(token_user_id)
            )
        )
        user_bookings = result.scalars().all()

        # If no bookings are found, respond gracefully
        if not user_bookings:
            return {"message": "No bookings found for this user.", "bookings": []}

        return {"bookings": jsonable_encoder(user_bookings)}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error fetching user bookings: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bookings.")


@router.get("/user-bookings/{user_id}")
async def get_user_bookings(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to fetch all bookings for a specific user by user_id.
    """
    try:
        # Fetch all bookings for the user from the database
        result = await db.execute(
            select(BookingModel).where(
                BookingModel.user_id == user_id
            )
        )
        user_bookings = result.scalars().all()

        # If no bookings are found, return an empty response
        if not user_bookings:
            return {"message": "No bookings found for this user.", "bookings": []}

        return {"bookings": jsonable_encoder(user_bookings)}

    except Exception as e:
        print(f"Error fetching user bookings: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bookings.")



async def get_user_role(request: Request):
    """Extract user role from the JWT token."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("role")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/room-availability")
async def get_available_rooms(
        db: AsyncSession = Depends(get_db),
        date: str = None,
        start_time: str = None,
        end_time: str = None,
):
    try:
        if not date:
            raise HTTPException(
                status_code=400, detail="The 'date' query parameter is required."
            )

        booking_date = datetime.strptime(date, "%Y-%m-%d").date()

        room_bookings_query = text("""
            SELECT r.id AS room_id, 
                   b.start_time AS booked_start_time, 
                   b.end_time AS booked_end_time
            FROM rooms r
            LEFT JOIN bookings b 
            ON r.id = b.room_id AND b.booking_date = :booking_date
        """)

        room_bookings_result = await db.execute(
            room_bookings_query, {"booking_date": booking_date}
        )
        room_bookings = room_bookings_result.fetchall()

        # Process room availability
        room_availability = {}
        for row in room_bookings:
            room_id = row[0]
            if room_id not in room_availability:
                room_availability[room_id] = {"booked_times": [], "available_times": []}

            booked_start_time = row[1]
            booked_end_time = row[2]

            if booked_start_time and booked_end_time:
                room_availability[room_id]["booked_times"].append(
                    (str(booked_start_time), str(booked_end_time))
                )

        # Compute available times
        full_day_slots = [f"{str(h).zfill(2)}:00" for h in range(24)]
        for room_id, room_data in room_availability.items():
            booked_times = room_data["booked_times"]

            room_data["available_times"] = [
                time_slot for time_slot in full_day_slots if not any(
                    booked_start <= time_slot < booked_end
                    for booked_start, booked_end in booked_times
                )
            ]

        return {"room_availability": jsonable_encoder(room_availability)}

    except Exception as e:
        await db.rollback()
        print(f"Error in /room-availability: {e}")
        raise HTTPException(status_code=500, detail="An error occurred.")


@router.post("/book-room")
async def book_room(booking: Booking, db: AsyncSession = Depends(get_db)):
    try:
        # Step 1: Check for conflicting bookings before creating a new one
        conflict_query = text("""
            SELECT 1 FROM bookings
            WHERE room_id = :room_id
              AND booking_date = :booking_date
              AND (
                  (:start_time BETWEEN start_time AND end_time) OR
                  (:end_time BETWEEN start_time AND end_time) OR
                  (start_time BETWEEN :start_time AND :end_time)
              )
        """)

        # Execute the query and pass parameters to avoid SQL injection
        result = await db.execute(conflict_query, {
            "room_id": booking.room_id,
            "booking_date": booking.booking_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
        })

        # Try to fetch the result
        conflicting_booking = result.scalar()  # Returns `1` if there is a conflict, otherwise `None`

        if conflicting_booking:
            raise HTTPException(
                status_code=400,
                detail="The room is already booked for the given date and time."
            )

        # Step 2: If no conflict, proceed to create the booking
        new_booking = BookingModel(
            user_id=booking.user_id,
            room_id=booking.room_id,
            booking_date=booking.booking_date,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
        )

        # Add the new booking and commit the transaction
        db.add(new_booking)
        await db.commit()
        await db.refresh(new_booking)  # Fetch the new booking data to access `id`

        return {"message": "Booking successful.", "booking_id": new_booking.id}

    except HTTPException as http_exc:
        # Explicitly handle HTTP exceptions
        raise http_exc

    except Exception as e:
        print(f"Error in booking room: {e}")  # For debugging purposes
        await db.rollback()  # Rollback any changes on failure
        raise HTTPException(status_code=500, detail="An error occurred while booking the room.")

@router.get("/admin-bookings")
async def get_admin_bookings(db: AsyncSession = Depends(get_db), user_role: str = Depends(get_user_role)):
    """
    Fetch all bookings for the current day.
    """
    if user_role is None:
        raise HTTPException(status_code=403, detail="User role missing in the token.")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access")

    try:
        today = date.today()
        # Use select() for AsyncSession
        result = await db.execute(
            select(BookingModel).where(BookingModel.booking_date == today)
        )
        bookings = result.scalars().all()  # Get the list of results

        if not bookings:
            return {"message": "No bookings found for today", "bookings": []}

        return {"bookings": jsonable_encoder(bookings)}
    except Exception as e:
        print(f"Error fetching admin bookings: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bookings.")
