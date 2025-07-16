import os

# Database
POSTGRES_DSN = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/seat_booking")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "mySectreKeyWhichWillChange")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
