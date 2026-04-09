from app.common.factories import create_batch_import_router
from app.contractors.models import Contractor as ContractorModel
from app.contractors.schemas import Contractor as ContractorSchema
from app.contractors.schemas import ContractorCreate

router = create_batch_import_router(
    model=ContractorModel,
    schema=ContractorSchema,
    create_schema=ContractorCreate,
    unique_col_name="name",
    prefix="/batch",
    tags=["Contractors"],
)
