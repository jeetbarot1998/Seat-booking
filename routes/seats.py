from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query

from database.session import db_pool, redis_client
from auth.service import AuthService, security
from services.booking import BookingService
from models import SeatResponse

router = APIRouter()
auth_service = AuthService(db_pool)

async def get_current_user(credentials = Depends(security)) -> int:
    """Extract and verify user_id from JWT token"""
    token = credentials.credentials
    user_id = auth_service.verify_token(token)
    return user_id

@router.get("/", response_model=List[SeatResponse])
async def get_available_seats(
    booking_date: Optional[date] = Query(None, description="Date to check availability"),
    section: Optional[str] = Query(None, description="Filter by section"),
    user_id: int = Depends(get_current_user)
):
    """Get available seats"""
    booking_service = BookingService(db_pool, redis_client)
    seats = await booking_service.get_available_seats(
        booking_date=booking_date or date.today(),
        section=section
    )

    return [
        SeatResponse(
            id=seat.id,
            section=seat.section,
            seat_number=seat.seat_number,
            is_available=True
        )
        for seat in seats
    ]