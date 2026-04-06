from app.schools.models import School as SchoolModel
from app.schools.schemas import SchoolCreate, School as SchoolSchema
from app.common.factories import create_batch_import_router

router = create_batch_import_router(
    model=SchoolModel,
    schema=SchoolSchema,
    create_schema=SchoolCreate,
    unique_col_name="code",
    prefix="/batch",
    tags=["Schools", "Batch"],
)
