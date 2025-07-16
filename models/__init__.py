from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator

# Data Models
@dataclass
class Seat:
    id: int
    section: str
    seat_number: str

@dataclass
class Booking:
    id: int
    seat_id: int
    user_id: int
    booking_date: date
    created_at: datetime
    status: str

@dataclass
class User:
    id: int
    username: str
    created_at: datetime

@dataclass
class BookingResult:
    success: bool
    booking: Optional[Booking] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

# Pydantic Models for API
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=3, description="Password")

class UserLoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 24 * 3600

class BookingRequest(BaseModel):
    seat_id: int = Field(..., description="ID of the seat to book")
    booking_date: Optional[date] = Field(None, description="Date for booking (defaults to today)")

    @validator('booking_date')
    def validate_booking_date(cls, v):
        if v and v < date.today():
            raise ValueError("Cannot book seats for past dates")
        if v and v > date.today() + timedelta(days=90):
            raise ValueError("Cannot book seats more than 90 days in advance")
        return v

class BookingResponse(BaseModel):
    id: int
    seat_id: int
    user_id: int
    booking_date: date
    created_at: datetime
    status: str
    seat_details: Dict[str, Any]

class SeatResponse(BaseModel):
    id: int
    section: str
    seat_number: str
    is_available: bool = True