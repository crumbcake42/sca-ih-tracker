from fastapi import FastAPI
from app.database import engine, Base

# You MUST import every model file here.
# This "registers" them with the Base.metadata so strings like "School" work.
from app.contractors import models as contractor_models
from app.employees import models as employee_models
from app.projects import models as project_models
from app.schools import models as school_models
from app.users import models as user_models

from app.contractors.router import router as contractors_router
from app.employees.router import router as employees_router
from app.projects.router import router as projects_router
from app.schools.router import router as schools_router
from app.users.router import auth_router, users_router

# Now create the tables in your L: drive /data/dev.db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SCA IH Tracker")

app.include_router(contractors_router)
app.include_router(employees_router)
app.include_router(projects_router)
app.include_router(schools_router)
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"status": "SCA IH Tracker API is running"}
