from app.common.factories import create_batch_import_router
from app.contractors.models import Contractor as ContractorModel
from app.contractors.schemas import ContractorCreate, Contractor as ContractorSchema

router = create_batch_import_router(
    model=ContractorModel,
    schema=ContractorSchema,
    create_schema=ContractorCreate,
    unique_col_name="name",
    prefix="/batch",
    tags=["Contractors"],
)
