from fastapi import FastAPI
from app.database import engine, Base

# You MUST import every model file here.
# This "registers" them with the Base.metadata so strings like "School" work.
from app.schools import models as school_models
from app.projects import models as project_models
from app.employees import models as employee_models
from app.contractors import models as contractor_models

# Now create the tables in your L: drive /data/dev.db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agency Toolbox")


@app.get("/")
def root():
    return {"status": "Agency Toolbox API is running"}
