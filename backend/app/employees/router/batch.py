from app.common.factories import create_batch_import_router
from app.employees.models import Employee as EmployeeModel
from app.employees.schemas import Employee as EmployeeSchema
from app.employees.schemas import EmployeeCreate

router = create_batch_import_router(
    model=EmployeeModel,
    schema=EmployeeSchema,
    create_schema=EmployeeCreate,
    unique_col_name="adp_id",
    prefix="/batch",
    tags=["Employees", "Batch"],
)
