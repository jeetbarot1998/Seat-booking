import asyncpg
import redis.asyncio as redis
import logging
from contextlib import asynccontextmanager
from typing import Optional
from configs.settings import POSTGRES_DSN, REDIS_URL

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self):
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=10,
            max_size=30,
            command_timeout=20
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def acquire(self):
        async with self.pool.acquire() as conn:
            yield conn

class RedisClient:
    def __init__(self, url: str):
        self.url = url
        self.client = None

    async def init(self):
        try:
            self.client = await redis.from_url(self.url, encoding="utf-8", decode_responses=True)
        except Exception as e:
            logger.error(f"init error as {str(e)}")

    async def close(self):
        if self.client:
            await self.client.close()

# Global instances
db_pool = DatabasePool(POSTGRES_DSN)
redis_client = RedisClient(REDIS_URL)

async def init_database(db_pool: DatabasePool):
    """Initialize database schema"""
    async with db_pool.acquire() as conn:
        # Create users table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create seats table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id SERIAL PRIMARY KEY,
            section VARCHAR(10) NOT NULL,
            seat_number VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section, seat_number)
        )
        """)

        # Create bookings table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            seat_id INTEGER NOT NULL REFERENCES seats(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            booking_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT one_booking_per_user_per_day 
                UNIQUE (user_id, booking_date, status) 
                DEFERRABLE INITIALLY DEFERRED
        )
        """)

        # Create indices
        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(booking_date);
        CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
        CREATE INDEX IF NOT EXISTS idx_bookings_confirmed_seats ON bookings (seat_id, booking_date) WHERE status = 'confirmed';
        """)

        # Insert sample seats if empty
        count = await conn.fetchval("SELECT COUNT(*) FROM seats")
        if count == 0:
            seats = []
            for section in ['Exhibitions', 'Elsevier', 'LNRS', 'Lexis Nexis']:
                for seat_num in range(1, 21):
                    seats.append((section, f"{seat_num:02d}"))

            await conn.executemany(
                "INSERT INTO seats (section, seat_number) VALUES ($1, $2)",
                seats
            )
            logger.info(f"Initialized {len(seats)} seats")