from app.common.factories import create_batch_import_router
from app.deliverables.models import Deliverable as DeliverableModel
from app.deliverables.schemas import Deliverable as DeliverableSchema
from app.deliverables.schemas import DeliverableCreate

router = create_batch_import_router(
    model=DeliverableModel,
    schema=DeliverableSchema,
    create_schema=DeliverableCreate,
    unique_col_name="name",
    prefix="/batch",
    tags=["Deliverables", "Batch"],
)
