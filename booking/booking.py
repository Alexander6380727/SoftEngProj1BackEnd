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
        db: AsyncSession = Depends(get_db), date: str = None, start_time: str = None):
    if not date or not start_time:
        raise HTTPException(status_code=400, detail="Both 'date' and 'start_time' query parameters are required.")
    try:
        from datetime import datetime

        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
        booking_start_time = datetime.strptime(start_time, "%H:%M").time()

        # Use `await` for executing queries against AsyncSession
        unavailable_rooms_result = await db.execute(
            select(BookingModel.room_id).where(
                BookingModel.booking_date == booking_date,
                BookingModel.start_time <= booking_start_time,
                BookingModel.end_time > booking_start_time
            )
        )
        unavailable_rooms = unavailable_rooms_result.scalars().all()

        # Use `await` for another query
        available_rooms_result = await db.execute(
            select(Room).where(~Room.id.in_(unavailable_rooms))
        )
        available_rooms = available_rooms_result.scalars().all()

    except Exception as e:
        # `rollback` must also be awaited
        await db.rollback()
        print(f"Error in /room-availability: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving room availability.")

    # Return the response
    return {"available_rooms": jsonable_encoder(available_rooms)}

@router.post("/book-room")
async def book_room(
        booking: Booking,  # Payload sent via request body
        request: Request,  # Request object to extract headers
        db: AsyncSession = Depends(get_db)  # Database session
):
    """
    Endpoint to create a booking for the authenticated user without using oauth2_scheme.
    """
    try:
        # Extract token from `Authorization` header
        auth_header = request.headers.get("Authorization")  # Extract Authorization header
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization token is missing or invalid"
            )

        token = auth_header.split(" ")[1]  # Extract the token (e.g., after 'Bearer ')

        # Decode the JWT token
        try:
            payload = jwt.decode(token, SECRET_KEY,
                                 algorithms=["HS256"])  # Replace "HS256" if using a different algorithm
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Extract `user_id` from token payload
        user_id = payload.get("sub")  # Substitute `sub` with the claim you're using for user identification
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: User ID missing")

        # Check for booking conflicts
        conflicting_bookings_query = select(BookingModel).where(
            BookingModel.room_id == booking.room_id,
            BookingModel.booking_date == booking.booking_date,
            BookingModel.start_time < booking.end_time,
            BookingModel.end_time > booking.start_time,
        )
        conflicting_bookings_result = await db.execute(conflicting_bookings_query)
        conflicting_bookings = conflicting_bookings_result.scalars().all()

        if conflicting_bookings:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected time slot is unavailable for the chosen room.",
            )

        # Create a new booking
        new_booking = BookingModel(
            user_id=int(user_id),  # Use `user_id` from the token
            room_id=booking.room_id,
            booking_date=booking.booking_date,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
        )
        db.add(new_booking)
        await db.commit()  # Commit the changes to the database
        return {"message": "Booking successful.", "booking_id": new_booking.id}

    except Exception as e:
        print(f"Error in booking room: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while booking the room.")

@router.get("/admin-bookings")
async def get_admin_bookings(db: Session = Depends(get_db), user_role: str = Depends(get_user_role)):
    """
    Fetch all bookings for the current day.
    """
    if user_role is None:
        raise HTTPException(status_code=403, detail="User role missing in the token.")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized access")

    today = date.today()
    bookings = db.query(BookingModel).filter(BookingModel.booking_date == today).all()

    if not bookings:
        return {"message": "No bookings found for today", "bookings": []}

    return {"bookings": bookings}
