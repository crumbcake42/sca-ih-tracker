from app.employees.models import Employee as EmployeeModel
from app.employees.schemas import EmployeeCreate, Employee as EmployeeSchema
from app.common.factories import create_batch_import_router

router = create_batch_import_router(
    model=EmployeeModel,
    schema=EmployeeSchema,
    create_schema=EmployeeCreate,
    unique_col_name="adp_id",
    prefix="/batch",
    tags=["Employees", "Batch"],
)
