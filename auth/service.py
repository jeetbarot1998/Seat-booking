import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.session import DatabasePool
from models import User
from configs.settings import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

security = HTTPBearer()

class AuthService:
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool

    async def register_user(self, username: str, password: str) -> User:
        """Register a new user"""
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)

        async with self.db.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (username, password_hash, created_at)
                    VALUES ($1, $2, $3)
                    RETURNING id, username, created_at
                    """,
                    username,
                    password_hash.decode('utf-8'),
                    datetime.utcnow()
                )

                return User(
                    id=row['id'],
                    username=row['username'],
                    created_at=row['created_at']
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already exists"
                    )
                raise

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user object"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, password_hash, created_at FROM users WHERE username = $1",
                username
            )

            if not row:
                return None

            if not bcrypt.checkpw(password.encode('utf-8'), row['password_hash'].encode('utf-8')):
                return None

            return User(
                id=row['id'],
                username=row['username'],
                created_at=row['created_at']
            )

    def create_access_token(self, user_id: int) -> str:
        """Create JWT token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> int:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload["user_id"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )