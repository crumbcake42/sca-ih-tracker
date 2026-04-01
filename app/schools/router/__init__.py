from fastapi import APIRouter, Depends

from app.users.dependencies import get_current_user
from .batch import router as batch_router

router = APIRouter(
    prefix="/schools", tags=["Schools"], dependencies=[Depends(get_current_user)]
)


router.include_router(batch_router)
