from fastapi import APIRouter, HTTPException, status

from database.session import db_pool
from auth.service import AuthService
from models import UserRegisterRequest, UserLoginRequest, TokenResponse

router = APIRouter()
auth_service = AuthService(db_pool)

@router.post("/register", response_model=TokenResponse)
async def register(user_request: UserRegisterRequest):
    """Register a new user and return JWT token"""
    user = await auth_service.register_user(user_request.username, user_request.password)
    access_token = auth_service.create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 3600
    )

@router.post("/login", response_model=TokenResponse)
async def login(login_request: UserLoginRequest):
    """Login with username and password, return JWT token"""
    user = await auth_service.authenticate_user(login_request.username, login_request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = auth_service.create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 3600
    )