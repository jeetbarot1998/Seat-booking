from fastapi import APIRouter, Depends, HTTPException

from database.session import db_pool
from auth.service import AuthService, security

router = APIRouter()
auth_service = AuthService(db_pool)


async def get_current_user(credentials=Depends(security)) -> int:
    """Extract and verify user_id from JWT token"""
    token = credentials.credentials
    user_id = auth_service.verify_token(token)
    return user_id


@router.get("/me")
async def get_current_user_info(user_id: int = Depends(get_current_user)):
    """Get current user information"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, created_at FROM users WHERE id = $1",
            user_id
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user['id'],
            "username": user['username'],
            "created_at": user['created_at']
        }
