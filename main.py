from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.authentication import router as auth_router
from calendar.routes import router as calendar_router
from booking.booking import router as booking_router  # Importing the booking router from the new directory

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
app.include_router(booking_router, prefix="/booking", tags=["Booking"])  # Including the booking router

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI backend"}
