from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from database.session import db_pool, redis_client
from auth.service import AuthService, security
from services.booking import BookingService
from models import BookingRequest, BookingResponse

router = APIRouter()
auth_service = AuthService(db_pool)

async def get_current_user(credentials = Depends(security)) -> int:
    """Extract and verify user_id from JWT token"""
    token = credentials.credentials
    user_id = auth_service.verify_token(token)
    return user_id

@router.post("/", response_model=BookingResponse)
async def create_booking(
    booking_request: BookingRequest,
    user_id: int = Depends(get_current_user)
):
    """Book a seat"""
    booking_service = BookingService(db_pool, redis_client)
    result = await booking_service.book_seat(
        seat_id=booking_request.seat_id,
        user_id=user_id,
        booking_date=booking_request.booking_date or date.today()
    )

    if not result.success:
        if result.error_code == "USER_ALREADY_BOOKED":
            raise HTTPException(status_code=400, detail="You already have a booking for this date")
        elif result.error_code == "SEAT_NOT_AVAILABLE":
            raise HTTPException(status_code=409, detail="Seat is not available")
        elif result.error_code == "LOCK_FAILED":
            raise HTTPException(status_code=429, detail="Seat is currently being booked. Please try again.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while booking the seat")

    booking = result.booking
    async with db_pool.acquire() as conn:
        seat_row = await conn.fetchrow("SELECT * FROM seats WHERE id = $1", booking.seat_id)

    return BookingResponse(
        id=booking.id,
        seat_id=booking.seat_id,
        user_id=booking.user_id,
        booking_date=booking.booking_date,
        created_at=booking.created_at,
        status=booking.status,
        seat_details={
            "section": seat_row['section'],
            "seat_number": seat_row['seat_number']
        }
    )

@router.get("/")
async def get_user_bookings(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    user_id: int = Depends(get_current_user)
):
    """Get current user's bookings"""
    booking_service = BookingService(db_pool, redis_client)
    bookings = await booking_service.get_user_bookings(
        user_id=user_id,
        from_date=from_date or date.today()
    )
    return bookings

@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: int = Path(..., description="Booking ID"),
    user_id: int = Depends(get_current_user)
):
    """Cancel a booking"""
    booking_service = BookingService(db_pool, redis_client)
    success = await booking_service.cancel_booking(booking_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found | already cancelled | does not belong to you.")

    return {"message": "Booking cancelled successfully"}