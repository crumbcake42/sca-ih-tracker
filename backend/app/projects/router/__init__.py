from fastapi import APIRouter

from .base import router as BaseRouter
from .hygienist import router as ProjectHygienistRouter
from .manager import router as ProjectManagerRouter

router = APIRouter(prefix="/projects", tags=["Projects"])
router.include_router(BaseRouter)
router.include_router(ProjectHygienistRouter)
router.include_router(ProjectManagerRouter)
