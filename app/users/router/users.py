from fastapi import APIRouter, Depends
from app.users.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user
