from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACodeCreate, WACode as WACodeSchema
from app.common.factories import create_batch_import_router

router = create_batch_import_router(
    model=WACodeModel,
    schema=WACodeSchema,
    create_schema=WACodeCreate,
    unique_col_name="code",
    prefix="/batch",
    tags=["WA Codes", "Batch"],
)
