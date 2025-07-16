# Seat Booking API

A high-performance seat booking system with JWT authentication, Redis caching, and PostgreSQL database.

## Features

- **JWT Authentication** - Secure user registration and login
- **Seat Booking** - Book seats with conflict prevention
- **Redis Caching** - Fast seat availability lookups
- **Distributed Locking** - Prevents race conditions during booking
- **User Management** - One booking per user per day limit

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL
- Redis

### Installation

1. Install dependencies:
```bash
pip install fastapi uvicorn asyncpg redis bcrypt pyjwt
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/seat_booking"
export REDIS_URL="redis://localhost:6379"
export JWT_SECRET="your-secret-key"
```

3. Run the server:
```bash
python fast-api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Seats & Bookings (Protected)
- `GET /seats` - Get available seats
- `POST /bookings` - Book a seat
- `GET /bookings` - Get user's bookings
- `DELETE /bookings/{id}` - Cancel booking

### User Info
- `GET /me` - Get current user info
- `GET /health` - Health check

## Database Schema

- **users** - User accounts with hashed passwords
- **seats** - Seat inventory (sections A-D, 20 seats each)
- **bookings** - Booking records with status tracking

## Architecture

- **FastAPI** - Web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and distributed locking
- **JWT** - Stateless authentication
- **Connection Pooling** - Optimized database connections

## Usage Example

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret"}'

# Book seat (use token from login)
curl -X POST http://localhost:8000/bookings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"seat_id": 1}'
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://user:password@localhost:5432/seat_booking` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `JWT_SECRET` | `mySectreKeyWhichWillChange` | JWT signing secret |

## Notes

- Users can only book one seat per day
- Bookings use distributed locking to prevent conflicts
- Seat availability is cached in Redis for 5 minutes
- Database schema is auto-created on first run