from fastapi import APIRouter, Depends

from app.users.dependencies import get_current_user

from .base import router as BaseRouter
from .deliverables import router as DeliverablesRouter
from .hygienist import router as ProjectHygienistRouter
from .manager import router as ProjectManagerRouter


router = APIRouter(
    prefix="/projects", tags=["Projects"], dependencies=[Depends(get_current_user)]
)
router.include_router(BaseRouter)
router.include_router(ProjectHygienistRouter)
router.include_router(ProjectManagerRouter)
router.include_router(DeliverablesRouter)
