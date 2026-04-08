from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine

from app.contractors.router import router as contractors_router
from app.deliverables.router import router as deliverables_router
from app.employees.router import router as employees_router
from app.hygienists.router import router as hygienists_router
from app.projects.router import router as projects_router
from app.schools.router import router as schools_router
from app.users.router import auth_router, users_router
from app.wa_codes.router import router as wa_codes_router


# Now create the tables in your ./data/dev.db
# Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: Create tables on the drive safely
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # The app is now running and serving requests

    # Shutdown: Clean up connections to dev.db
    await engine.dispose()


app = FastAPI(title="SCA IH Tracker")

app.include_router(contractors_router)
app.include_router(deliverables_router)
app.include_router(employees_router)
app.include_router(hygienists_router)
app.include_router(projects_router)
app.include_router(schools_router)
app.include_router(wa_codes_router)
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"status": "SCA IH Tracker API is running"}
