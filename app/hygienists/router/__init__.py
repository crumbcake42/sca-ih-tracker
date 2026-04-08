from fastapi import APIRouter, Depends
from app.users.dependencies import get_current_user
from .base import router as base_router

router = APIRouter(
    prefix="/hygienists", tags=["Hygienists"], dependencies=[Depends(get_current_user)]
)

router.include_router(base_router)
