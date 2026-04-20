from fastapi import APIRouter, Depends

from app.users.dependencies import get_current_user
from app.users.schemas import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=User)
async def get_me(current_user=Depends(get_current_user)):
    return current_user
