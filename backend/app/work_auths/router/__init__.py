from fastapi import APIRouter

from .base import router as BaseRouter
from .building_codes import router as BuildingCodesRouter
from .project_codes import router as ProjectCodesRouter
from .rfas import router as RFAsRouter

router = APIRouter(prefix="/work-auths", tags=["Work Auths"])
router.include_router(BaseRouter)
router.include_router(BuildingCodesRouter)
router.include_router(ProjectCodesRouter)
router.include_router(RFAsRouter)
