from fastapi import APIRouter, Depends

from app.users.dependencies import get_current_user

from .batches import router as batches_router
from .config import router as config_router

router = APIRouter(
    prefix="/lab-results",
    tags=["Lab Results"],
    dependencies=[Depends(get_current_user)],
)

router.include_router(config_router)
router.include_router(batches_router)
