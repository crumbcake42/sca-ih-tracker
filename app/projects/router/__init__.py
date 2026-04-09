from fastapi import APIRouter

from .base import router as BaseRouter
from .hygienist import router as ProjectHygienistRouter

router = APIRouter(prefix="/projects", tags=["Projects"])
router.include_router(BaseRouter)
router.include_router(ProjectHygienistRouter)
