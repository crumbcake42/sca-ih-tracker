"""
Unit tests for get_blocking_notes_for_project() in app/projects/services.py.

Tests call the service function directly against db_session; no HTTP.
All tests roll back via the conftest transaction fixture.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    Boro,
    EmployeeRoleType,
    NoteEntityType,
    WACodeLevel,
)
from app.deliverables.models import Deliverable, ProjectDeliverable
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import SampleBatch, SampleType
from app.notes.models import Note
from app.projects.models import Project
from app.projects.services import get_blocking_notes_for_project
from app.schools.models import School

if TYPE_CHECKING:
    from app.time_entries.models import TimeEntry

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K099",
        name="Test School",
        address="1 Test St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School, *, suffix: str = "01") -> Project:
    project = Project(name="Test Project", project_number=f"26-999-{suffix:>04}")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_employee(db: AsyncSession) -> Employee:
    emp = Employee(first_name="Jane", last_name="Tester")
    db.add(emp)
    await db.flush()
    return emp


async def _seed_role(db: AsyncSession, employee: Employee) -> EmployeeRole:
    role = EmployeeRole(
        employee_id=employee.id,
        role_type=EmployeeRoleType.ACM_PROJECT_MONITOR,
        start_date=date(2025, 1, 1),
        end_date=None,
        hourly_rate="75.00",
    )
    db.add(role)
    await db.flush()
    return role


async def _seed_time_entry(
    db: AsyncSession,
    project: Project,
    school: School,
    employee: Employee,
    role: EmployeeRole,
) -> "TimeEntry":
    from app.time_entries.models import TimeEntry

    entry = TimeEntry(
        start_datetime=datetime(2025, 6, 1, 9, 0, 0),
        end_datetime=datetime(2025, 6, 1, 17, 0, 0),
        employee_id=employee.id,
        employee_role_id=role.id,
        project_id=project.id,
        school_id=school.id,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(entry)
    await db.flush()
    return entry


async def _seed_sample_type(db: AsyncSession) -> SampleType:
    st = SampleType(name="PCM-Test", created_by_id=SYSTEM_USER_ID, updated_by_id=SYSTEM_USER_ID)
    db.add(st)
    await db.flush()
    return st


async def _seed_batch(db: AsyncSession, time_entry, sample_type: SampleType) -> SampleBatch:
    batch = SampleBatch(
        sample_type_id=sample_type.id,
        time_entry_id=time_entry.id,
        batch_num=f"BATCH-{time_entry.id}-TST",
        is_report=False,
        date_collected=date(2025, 6, 1),
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _seed_deliverable(db: AsyncSession) -> Deliverable:
    deliv = Deliverable(
        name="Air Clearance Test",
        level=WACodeLevel.PROJECT,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(deliv)
    await db.flush()
    return deliv


async def _seed_project_deliverable(
    db: AsyncSession, project: Project, deliverable: Deliverable
) -> ProjectDeliverable:
    pd = ProjectDeliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pd)
    await db.flush()
    return pd


async def _seed_blocking_note(
    db: AsyncSession,
    entity_type: NoteEntityType,
    entity_id: int,
    body: str = "Blocking issue",
    *,
    resolved: bool = False,
) -> Note:
    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body=body,
        is_blocking=True,
        is_resolved=resolved,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    if resolved:
        note.resolved_by_id = SYSTEM_USER_ID
        note.resolved_at = datetime.now(tz=UTC)
    db.add(note)
    await db.flush()
    return note


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetBlockingNotesForProject:
    async def test_empty_returns_empty_list(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="00")

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result == []

    async def test_returns_project_level_note(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="02")

        await _seed_blocking_note(db_session, NoteEntityType.PROJECT, project.id, "Project issue")

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.PROJECT
        assert result[0].entity_id == project.id
        assert result[0].body == "Project issue"
        assert result[0].link == f"/projects/{project.id}"

    async def test_returns_time_entry_note(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="03")
        emp = await _seed_employee(db_session)
        role = await _seed_role(db_session, emp)
        entry = await _seed_time_entry(db_session, project, school, emp, role)

        await _seed_blocking_note(db_session, NoteEntityType.TIME_ENTRY, entry.id)

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.TIME_ENTRY
        assert result[0].entity_id == entry.id
        assert result[0].link == f"/time-entries/{entry.id}"

    async def test_returns_sample_batch_note(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="04")
        emp = await _seed_employee(db_session)
        role = await _seed_role(db_session, emp)
        entry = await _seed_time_entry(db_session, project, school, emp, role)
        st = await _seed_sample_type(db_session)
        batch = await _seed_batch(db_session, entry, st)

        await _seed_blocking_note(db_session, NoteEntityType.SAMPLE_BATCH, batch.id)

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.SAMPLE_BATCH
        assert result[0].entity_id == batch.id
        assert result[0].link == f"/lab-results/batches/{batch.id}"

    async def test_returns_deliverable_note(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="05")
        deliv = await _seed_deliverable(db_session)
        await _seed_project_deliverable(db_session, project, deliv)

        await _seed_blocking_note(db_session, NoteEntityType.DELIVERABLE, deliv.id)

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.DELIVERABLE
        assert result[0].entity_id == deliv.id
        assert result[0].link == f"/deliverables/{deliv.id}"

    async def test_excludes_resolved_notes(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="06")

        await _seed_blocking_note(
            db_session, NoteEntityType.PROJECT, project.id, resolved=True
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result == []

    async def test_excludes_other_projects_time_entry(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project_a = await _seed_project(db_session, school, suffix="07")
        project_b = await _seed_project(db_session, school, suffix="08")
        emp = await _seed_employee(db_session)
        role = await _seed_role(db_session, emp)

        # Time entry belongs to project_b, not project_a
        entry_b = await _seed_time_entry(db_session, project_b, school, emp, role)
        await _seed_blocking_note(db_session, NoteEntityType.TIME_ENTRY, entry_b.id)

        result = await get_blocking_notes_for_project(project_a.id, db_session)

        assert result == []

    async def test_ordered_by_created_at(self, db_session: AsyncSession):
        """Notes are returned in ascending created_at order."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="09")

        # Insert three notes on the project; DB will assign ascending created_at
        for body in ("First", "Second", "Third"):
            await _seed_blocking_note(db_session, NoteEntityType.PROJECT, project.id, body)

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 3
        assert result[0].body == "First"
        assert result[1].body == "Second"
        assert result[2].body == "Third"

    async def test_entity_label_format(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="10")
        emp = await _seed_employee(db_session)
        role = await _seed_role(db_session, emp)
        entry = await _seed_time_entry(db_session, project, school, emp, role)

        await _seed_blocking_note(db_session, NoteEntityType.TIME_ENTRY, entry.id)

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result[0].entity_label == f"Time Entry #{entry.id}"
