from app.common.factories import create_readonly_router
from app.deliverables.models import Deliverable as DeliverableModel
from app.deliverables.schemas import Deliverable as DeliverableSchema

router = create_readonly_router(
    model=DeliverableModel,
    read_schema=DeliverableSchema,
    default_sort=DeliverableModel.name.asc(),
    search_attr=DeliverableModel.name,
)
