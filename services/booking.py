import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from database.session import DatabasePool, RedisClient
from models import Seat, Booking, BookingResult

logger = logging.getLogger(__name__)

class BookingService:
    def __init__(self, db_pool: DatabasePool, redis_client: RedisClient):
        self.db = db_pool
        self.redis = redis_client.client

    async def book_seat(self, seat_id: int, user_id: int,
                       booking_date: Optional[date] = None) -> BookingResult:
        """Book a seat with distributed locking"""
        if not booking_date:
            booking_date = date.today()

        lock_key = f"lock:seat:{seat_id}:{booking_date}"
        lock_token = f"{user_id}:{datetime.utcnow().timestamp()}"

        if not await self.redis.set(lock_key, lock_token, ex=10, nx=True):
            return BookingResult(
                success=False,
                error_code="LOCK_FAILED",
                error_message="Seat is currently being booked by another user. Please try again."
            )

        try:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Check if user already has a booking for this date
                    existing_check = """
                    SELECT id FROM bookings 
                    WHERE user_id = $1 AND booking_date = $2 AND status = 'confirmed'
                    LIMIT 1
                    """
                    existing = await conn.fetchrow(existing_check, user_id, booking_date)
                    if existing:
                        return BookingResult(
                            success=False,
                            error_code="USER_ALREADY_BOOKED",
                            error_message="User already has a booking for this date"
                        )

                    # Check if seat is available
                    availability_check = """
                    SELECT s.id 
                    FROM seats s
                    WHERE s.id = $1 
                    AND NOT EXISTS (
                        SELECT 1 FROM bookings b 
                        WHERE b.seat_id = s.id 
                        AND b.booking_date = $2 
                        AND b.status = 'confirmed'
                    )
                    """
                    seat = await conn.fetchrow(availability_check, seat_id, booking_date)
                    if not seat:
                        return BookingResult(
                            success=False,
                            error_code="SEAT_NOT_AVAILABLE",
                            error_message="Seat is not available for the selected date"
                        )

                    # Create booking
                    insert_query = """
                    INSERT INTO bookings (seat_id, user_id, booking_date, status, created_at)
                    VALUES ($1, $2, $3, 'confirmed', $4)
                    RETURNING id, seat_id, user_id, booking_date, created_at, status
                    """
                    row = await conn.fetchrow(
                        insert_query,
                        seat_id,
                        user_id,
                        booking_date,
                        datetime.utcnow()
                    )

                    booking = Booking(
                        id=row['id'],
                        seat_id=row['seat_id'],
                        user_id=row['user_id'],
                        booking_date=row['booking_date'],
                        created_at=row['created_at'],
                        status=row['status']
                    )

                    await self._invalidate_availability_cache(booking_date)
                    logger.info(f"Successfully booked seat {seat_id} for user {user_id}")
                    return BookingResult(success=True, booking=booking)

        except Exception as e:
            logger.error(f"Error booking seat: {e}")
            return BookingResult(
                success=False,
                error_code="BOOKING_ERROR",
                error_message="An error occurred while booking the seat"
            )
        finally:
            await self.redis.delete(lock_key)

    async def get_available_seats(self, booking_date: Optional[date] = None,
                                section: Optional[str] = None) -> List[Seat]:
        """Get available seats with caching"""
        if not booking_date:
            booking_date = date.today()

        cache_key = f"available_seats:{booking_date}"
        if section:
            cache_key += f":section:{section}"

        cached = await self.redis.get(cache_key)
        if cached:
            seats_data = json.loads(cached)
            return [Seat(**seat) for seat in seats_data]

        query = """
        SELECT s.id, s.section, s.seat_number
        FROM seats s
        LEFT JOIN bookings b ON s.id = b.seat_id 
            AND b.booking_date = $1 
            AND b.status = 'confirmed'
        WHERE b.id IS NULL
        """
        params = [booking_date]

        if section is not None:
            query += f" AND s.section = ${len(params) + 1}"
            params.append(section)

        query += " ORDER BY s.section, s.seat_number"

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            seats = []
            seats_data = []
            for row in rows:
                seat = Seat(
                    id=row['id'],
                    section=row['section'],
                    seat_number=row['seat_number']
                )
                seats.append(seat)
                seats_data.append({
                    "id": row['id'],
                    "section": row['section'],
                    "seat_number": row['seat_number']
                })

            await self.redis.set(cache_key, json.dumps(seats_data), ex=300)
            return seats

    async def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        """Cancel a booking"""
        async with self.db.acquire() as conn:
            get_query = """
            SELECT booking_date FROM bookings 
            WHERE id = $1 AND user_id = $2 AND status = 'confirmed'
            """
            booking = await conn.fetchrow(get_query, booking_id, user_id)
            if not booking:
                return False

            cancel_query = """
                UPDATE bookings 
                SET status = 'cancelled', updated_at = $3
                WHERE id = $1 AND user_id = $2 AND status = 'confirmed'
                RETURNING id
            """
            result = await conn.fetchrow(cancel_query, booking_id, user_id, datetime.utcnow())

            if result:
                await self._invalidate_availability_cache(booking['booking_date'])
                return True
            return False

    async def get_user_bookings(self, user_id: int,
                               from_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get user bookings"""
        if not from_date:
            from_date = date.today()

        query = """
        SELECT b.id, b.seat_id, b.user_id, b.booking_date, b.created_at, b.status,
               s.section, s.seat_number
        FROM bookings b
        JOIN seats s ON b.seat_id = s.id
        WHERE b.user_id = $1 AND b.booking_date >= $2 AND b.status = 'confirmed'
        ORDER BY b.booking_date, s.section, s.seat_number
        """

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id, from_date)
            return [
                {
                    "id": row['id'],
                    "seat_id": row['seat_id'],
                    "user_id": row['user_id'],
                    "booking_date": row['booking_date'],
                    "created_at": row['created_at'],
                    "status": row['status'],
                    "seat_details": {
                        "section": row['section'],
                        "seat_number": row['seat_number']
                    }
                }
                for row in rows
            ]

    async def _invalidate_availability_cache(self, booking_date: date):
        """Invalidate cache for a specific date"""
        pattern = f"available_seats:{booking_date}*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break