from app.common.factories import create_batch_import_router
from app.employees.models import Employee as EmployeeModel
from app.employees.schemas import Employee as EmployeeSchema
from app.employees.schemas import EmployeeCreate
from app.employees.service import generate_unique_display_name


async def _set_display_name(db, obj_in: EmployeeCreate, _row_dict: dict) -> EmployeeCreate:
    if obj_in.display_name:
        return obj_in
    display_name = await generate_unique_display_name(db, obj_in.first_name, obj_in.last_name)
    return obj_in.model_copy(update={"display_name": display_name})


router = create_batch_import_router(
    model=EmployeeModel,
    schema=EmployeeSchema,
    create_schema=EmployeeCreate,
    unique_col_name="adp_id",
    prefix="/batch",
    tags=["Employees", "Batch"],
    custom_validator=_set_display_name,
)
