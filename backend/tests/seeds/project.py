import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project
from app.schools.models import School

_counter = itertools.count(1)


async def seed_project(
    db: AsyncSession, school: School, *, project_number: str | None = None, **overrides
) -> Project:
    n = next(_counter)
    project = Project(
        name=overrides.pop("name", "Test Project"),
        project_number=project_number or f"26-{n:03d}-{n:04d}",
        **overrides,
    )
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project
