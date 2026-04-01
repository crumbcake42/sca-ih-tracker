from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.users.dependencies import PermissionChecker, PermissionName

# Import your models and schemas
from app.projects import models, schemas

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[schemas.Project])
def get_projects(
    skip: int = 0,
    limit: int = 100,
    title_search: str | None = Query(None, description="Filter by project title"),
    db: Session = Depends(get_db),
):
    """Get project list with optional pagination and search."""
    query = db.query(models.Project)

    if title_search:
        query = query.filter(models.Project.title.contains(title_search))

    return query.offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=schemas.Project,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_CREATE))],
)
def create_project(project_in: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project (Requires PROJECT_CREATE permission)."""
    new_project = models.Project(**project_in.model_dump())
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/{project_id}", response_model=schemas.Project)
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    """Get a single project with its related School and Contractor details."""
    project = (
        db.query(models.Project)
        .options(joinedload(models.Project.school))
        .options(joinedload(models.Project.contractor))
        .filter(models.Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch(
    "/{project_id}",
    response_model=schemas.Project,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_EDIT))],
)
def update_project(
    project_id: int,
    project_update: schemas.ProjectCreate,  # Using Create schema for simplicity, or make a ProjectUpdate schema
    db: Session = Depends(get_db),
):
    """Update project details (Requires PROJECT_EDIT permission)."""
    db_project = (
        db.query(models.Project).filter(models.Project.id == project_id).first()
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update only the fields provided
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)

    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PermissionName.PROJECT_DELETE))],
)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Permanently delete a project (Requires PROJECT_DELETE permission)."""
    db_project = (
        db.query(models.Project).filter(models.Project.id == project_id).first()
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(db_project)
    db.commit()
    return None
