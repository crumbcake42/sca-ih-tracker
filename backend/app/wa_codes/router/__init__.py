from fastapi import APIRouter, Depends

from app.requirement_triggers.router import router as requirement_triggers_router
from app.users.dependencies import get_current_user

from .base import router as base_router
from .batch import router as batch_router

router = APIRouter(
    prefix="/wa-codes", tags=["WA Codes"], dependencies=[Depends(get_current_user)]
)

router.include_router(base_router)
router.include_router(batch_router)
router.include_router(requirement_triggers_router)
