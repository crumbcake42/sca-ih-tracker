from app.common.factories import create_batch_import_router
from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACode as WACodeSchema
from app.wa_codes.schemas import WACodeCreate

router = create_batch_import_router(
    model=WACodeModel,
    schema=WACodeSchema,
    create_schema=WACodeCreate,
    unique_col_name="code",
    prefix="/batch",
    tags=["WA Codes", "Batch"],
)
