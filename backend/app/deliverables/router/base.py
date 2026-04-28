from fastapi import APIRouter

from app.common.factories import create_guarded_delete_router, create_readonly_router
from app.deliverables.models import (
    Deliverable as DeliverableModel,
)
from app.deliverables.models import (
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.deliverables.schemas import Deliverable as DeliverableSchema

router = APIRouter()

router.include_router(
    create_readonly_router(
        model=DeliverableModel,
        read_schema=DeliverableSchema,
        default_sort=DeliverableModel.name.asc(),
        search_attr=DeliverableModel.name,
    )
)


router.include_router(
    create_guarded_delete_router(
        model=DeliverableModel,
        not_found_detail="Deliverable not found",
        refs=[
            (ProjectDeliverable, ProjectDeliverable.deliverable_id, "project_deliverables"),
            (ProjectBuildingDeliverable, ProjectBuildingDeliverable.deliverable_id, "project_building_deliverables"),
            (DeliverableWACodeTrigger, DeliverableWACodeTrigger.deliverable_id, "deliverable_wa_code_triggers"),
        ],
        path_param_name="deliverable_id",
    )
)
