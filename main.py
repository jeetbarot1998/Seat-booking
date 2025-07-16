from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from database.session import db_pool, redis_client, init_database
import routes.auth as auth
import routes.bookings as bookings
import routes.seats as seats
import routes.users as users

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    await db_pool.init()
    await redis_client.init()
    # await init_database(db_pool)
    logger.info("Startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await redis_client.close()
    await db_pool.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Seat Booking API with JWT Auth",
    description="High-performance seat booking with JWT authentication",
    version="3.0.0",
    contact={
        "name": "Seat Booking",
        "email": "jeetbarot1998@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
app.include_router(seats.router, prefix="/seats", tags=["Seats"])
app.include_router(users.router, prefix="/users", tags=["Users"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)