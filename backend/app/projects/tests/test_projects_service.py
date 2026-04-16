"""
Unit tests for project services in app/projects/services.py.

Tests call service functions directly against db_session; no HTTP.
All tests roll back via the conftest transaction fixture.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    Boro,
    EmployeeRoleType,
    NoteEntityType,
    NoteType,
    SCADeliverableStatus,
    WACodeLevel,
    WACodeStatus,
)
from app.deliverables.models import (
    Deliverable,
    DeliverableWACodeTrigger,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.employees.models import Employee, EmployeeRole
from app.lab_results.models import SampleBatch, SampleType, SampleTypeWACode
from app.notes.models import Note
from app.projects.models import Project
from app.projects.services import (
    check_sample_type_gap_note,
    ensure_deliverables_exist,
    get_blocking_notes_for_project,
    recalculate_deliverable_sca_status,
)
from app.schools.models import School
from app.wa_codes.models import WACode
from app.work_auths.models import WorkAuth, WorkAuthBuildingCode, WorkAuthProjectCode

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


# ---------------------------------------------------------------------------
# Additional seed helpers for Phase 6 Session A tests
# ---------------------------------------------------------------------------


_wa_seq = 0


def _next_wa_num() -> str:
    global _wa_seq
    _wa_seq += 1
    return f"WA-{_wa_seq:04d}"


async def _seed_wa_code(
    db: AsyncSession, *, code: str, level: WACodeLevel
) -> WACode:
    wa_code = WACode(
        code=code,
        description=f"Test code {code}",
        level=level,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(wa_code)
    await db.flush()
    return wa_code


async def _seed_work_auth(db: AsyncSession, project: Project) -> WorkAuth:
    num = _next_wa_num()
    wa = WorkAuth(
        wa_num=num,
        service_id=f"SVC-{num}",
        project_num=f"PN-{num}",
        initiation_date=date(2025, 1, 1),
        project_id=project.id,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(wa)
    await db.flush()
    return wa


async def _seed_wa_project_code(
    db: AsyncSession,
    wa: WorkAuth,
    wa_code: WACode,
    status: WACodeStatus = WACodeStatus.ACTIVE,
) -> WorkAuthProjectCode:
    pc = WorkAuthProjectCode(
        work_auth_id=wa.id,
        wa_code_id=wa_code.id,
        fee=Decimal("100.00"),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pc)
    await db.flush()
    return pc


async def _seed_wa_building_code(
    db: AsyncSession,
    wa: WorkAuth,
    wa_code: WACode,
    project: Project,
    school: School,
    status: WACodeStatus = WACodeStatus.ACTIVE,
) -> WorkAuthBuildingCode:
    bc = WorkAuthBuildingCode(
        work_auth_id=wa.id,
        wa_code_id=wa_code.id,
        project_id=project.id,
        school_id=school.id,
        budget=Decimal("1000.00"),
        status=status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(bc)
    await db.flush()
    return bc


async def _seed_deliverable_with_trigger(
    db: AsyncSession,
    *,
    name: str,
    level: WACodeLevel,
    wa_code: WACode,
) -> Deliverable:
    deliv = Deliverable(
        name=name,
        level=level,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(deliv)
    await db.flush()
    trigger = DeliverableWACodeTrigger(deliverable_id=deliv.id, wa_code_id=wa_code.id)
    db.add(trigger)
    await db.flush()
    return deliv


async def _seed_project_deliverable_row(
    db: AsyncSession,
    project: Project,
    deliverable: Deliverable,
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA,
) -> ProjectDeliverable:
    pd = ProjectDeliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        sca_status=sca_status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pd)
    await db.flush()
    return pd


async def _seed_building_deliverable_row(
    db: AsyncSession,
    project: Project,
    deliverable: Deliverable,
    school: School,
    sca_status: SCADeliverableStatus = SCADeliverableStatus.PENDING_WA,
) -> ProjectBuildingDeliverable:
    pbd = ProjectBuildingDeliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        school_id=school.id,
        sca_status=sca_status,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(pbd)
    await db.flush()
    return pbd


# ---------------------------------------------------------------------------
# Tests: recalculate_deliverable_sca_status
# ---------------------------------------------------------------------------


class TestRecalculateDeliverableSCAStatus:
    async def test_no_wa_sets_all_derivable_to_pending_wa(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="20")
        wa_code = await _seed_wa_code(db_session, code="A-20", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 20", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        # Start at OUTSTANDING; no WA on the project
        pd = await _seed_project_deliverable_row(
            db_session, project, deliv, SCADeliverableStatus.OUTSTANDING
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

    async def test_active_code_sets_outstanding(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="21")
        wa_code = await _seed_wa_code(db_session, code="A-21", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 21", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.ACTIVE)
        pd = await _seed_project_deliverable_row(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_added_by_rfa_code_sets_outstanding(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="22")
        wa_code = await _seed_wa_code(db_session, code="A-22", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 22", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.ADDED_BY_RFA)
        pd = await _seed_project_deliverable_row(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_rfa_needed_code_sets_pending_rfa(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="23")
        wa_code = await _seed_wa_code(db_session, code="A-23", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 23", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.RFA_NEEDED)
        pd = await _seed_project_deliverable_row(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_rfa_pending_code_sets_pending_rfa(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="24")
        wa_code = await _seed_wa_code(db_session, code="A-24", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 24", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.RFA_PENDING)
        pd = await _seed_project_deliverable_row(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_removed_code_treated_as_absent(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="25")
        wa_code = await _seed_wa_code(db_session, code="A-25", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 25", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.REMOVED)
        pd = await _seed_project_deliverable_row(
            db_session, project, deliv, SCADeliverableStatus.OUTSTANDING
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

    async def test_manual_statuses_untouched(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="26")
        wa_code = await _seed_wa_code(db_session, code="A-26", level=WACodeLevel.PROJECT)
        deliv_a = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 26a", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        deliv_b = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 26b", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        deliv_c = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 26c", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.ACTIVE)

        pd_ur = await _seed_project_deliverable_row(
            db_session, project, deliv_a, SCADeliverableStatus.UNDER_REVIEW
        )
        pd_rej = await _seed_project_deliverable_row(
            db_session, project, deliv_b, SCADeliverableStatus.REJECTED
        )
        pd_app = await _seed_project_deliverable_row(
            db_session, project, deliv_c, SCADeliverableStatus.APPROVED
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd_ur)
        await db_session.refresh(pd_rej)
        await db_session.refresh(pd_app)

        assert pd_ur.sca_status == SCADeliverableStatus.UNDER_REVIEW
        assert pd_rej.sca_status == SCADeliverableStatus.REJECTED
        assert pd_app.sca_status == SCADeliverableStatus.APPROVED

    async def test_building_level_deliverable_updated(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="27")
        wa_code = await _seed_wa_code(db_session, code="B-27", level=WACodeLevel.BUILDING)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Bldg Deliv 27", level=WACodeLevel.BUILDING, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_building_code(
            db_session, wa, wa_code, project, school, WACodeStatus.ACTIVE
        )
        pbd = await _seed_building_deliverable_row(db_session, project, deliv, school)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pbd)

        assert pbd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_building_level_rfa_needed_sets_pending_rfa(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="28")
        wa_code = await _seed_wa_code(db_session, code="B-28", level=WACodeLevel.BUILDING)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Bldg Deliv 28", level=WACodeLevel.BUILDING, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_building_code(
            db_session, wa, wa_code, project, school, WACodeStatus.RFA_NEEDED
        )
        pbd = await _seed_building_deliverable_row(db_session, project, deliv, school)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pbd)

        assert pbd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_status_promotion_chain(self, db_session: AsyncSession):
        """Verify pending_wa → pending_rfa → outstanding promotion sequence."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="29")
        wa_code = await _seed_wa_code(db_session, code="A-29", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 29", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        pd = await _seed_project_deliverable_row(db_session, project, deliv)

        # Stage 1: no WA → pending_wa (already the default)
        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)
        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

        # Stage 2: WA added with rfa_needed code → pending_rfa
        wa = await _seed_work_auth(db_session, project)
        pc = await _seed_wa_project_code(db_session, wa, wa_code, WACodeStatus.RFA_NEEDED)
        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)
        assert pd.sca_status == SCADeliverableStatus.PENDING_RFA

        # Stage 3: code becomes active → outstanding
        pc.status = WACodeStatus.ACTIVE
        await db_session.flush()
        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)
        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING


# ---------------------------------------------------------------------------
# Tests: ensure_deliverables_exist
# ---------------------------------------------------------------------------


class TestEnsureDeliverablesExist:
    async def test_no_wa_creates_nothing(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="30")
        wa_code = await _seed_wa_code(db_session, code="A-30", level=WACodeLevel.PROJECT)
        await _seed_deliverable_with_trigger(
            db_session, name="Deliv 30", level=WACodeLevel.PROJECT, wa_code=wa_code
        )

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        result = (await db_session.execute(
            _select(ProjectDeliverable).where(ProjectDeliverable.project_id == project.id)
        )).scalars().all()
        assert result == []

    async def test_creates_project_level_deliverable(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="31")
        wa_code = await _seed_wa_code(db_session, code="A-31", level=WACodeLevel.PROJECT)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Deliv 31", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(ProjectDeliverable).where(ProjectDeliverable.project_id == project.id)
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].deliverable_id == deliv.id

    async def test_creates_building_level_deliverable(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="32")
        wa_code = await _seed_wa_code(db_session, code="B-32", level=WACodeLevel.BUILDING)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Bldg Deliv 32", level=WACodeLevel.BUILDING, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_building_code(db_session, wa, wa_code, project, school)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(ProjectBuildingDeliverable).where(
                ProjectBuildingDeliverable.project_id == project.id
            )
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].deliverable_id == deliv.id
        assert rows[0].school_id == school.id

    async def test_idempotent(self, db_session: AsyncSession):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="33")
        wa_code = await _seed_wa_code(db_session, code="A-33", level=WACodeLevel.PROJECT)
        await _seed_deliverable_with_trigger(
            db_session, name="Deliv 33", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)
        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(ProjectDeliverable).where(ProjectDeliverable.project_id == project.id)
        )).scalars().all()
        assert len(rows) == 1

    async def test_does_not_create_project_deliv_for_building_code(
        self, db_session: AsyncSession
    ):
        """A building-level code should not produce a project-level deliverable."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="34")
        bldg_code = await _seed_wa_code(db_session, code="B-34", level=WACodeLevel.BUILDING)
        await _seed_deliverable_with_trigger(
            db_session, name="Bldg Deliv 34", level=WACodeLevel.BUILDING, wa_code=bldg_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_building_code(db_session, wa, bldg_code, project, school)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        proj_rows = (await db_session.execute(
            _select(ProjectDeliverable).where(ProjectDeliverable.project_id == project.id)
        )).scalars().all()
        assert proj_rows == []

    async def test_no_trigger_creates_nothing(self, db_session: AsyncSession):
        """A WA code with no deliverable trigger produces no rows."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="35")
        wa_code = await _seed_wa_code(db_session, code="A-35", level=WACodeLevel.PROJECT)
        # No DeliverableWACodeTrigger created
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(ProjectDeliverable).where(ProjectDeliverable.project_id == project.id)
        )).scalars().all()
        assert rows == []

    async def test_building_deliv_created_per_school(self, db_session: AsyncSession):
        """Building-level deliverable creates one row per linked school."""
        school_a = await _seed_school(db_session)
        project = await _seed_project(db_session, school_a, suffix="36")
        # Link a second school
        school_b = School(
            code="M036",
            name="Second School 36",
            address="2 Test Ave",
            city=Boro.MANHATTAN,
            state="NY",
            zip_code="10001",
        )
        db_session.add(school_b)
        await db_session.flush()
        project.schools.append(school_b)
        await db_session.flush()

        wa_code = await _seed_wa_code(db_session, code="B-36", level=WACodeLevel.BUILDING)
        deliv = await _seed_deliverable_with_trigger(
            db_session, name="Bldg Deliv 36", level=WACodeLevel.BUILDING, wa_code=wa_code
        )
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_building_code(db_session, wa, wa_code, project, school_a)
        await _seed_wa_building_code(db_session, wa, wa_code, project, school_b)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(ProjectBuildingDeliverable).where(
                ProjectBuildingDeliverable.project_id == project.id,
                ProjectBuildingDeliverable.deliverable_id == deliv.id,
            )
        )).scalars().all()
        school_ids = {r.school_id for r in rows}
        assert len(rows) == 2
        assert school_a.id in school_ids
        assert school_b.id in school_ids


# ---------------------------------------------------------------------------
# TestCheckSampleTypeGapNote
# ---------------------------------------------------------------------------


class TestCheckSampleTypeGapNote:
    async def test_no_wa_returns_early(self, db_session: AsyncSession):
        """With no WA on the project, function is a no-op (no error)."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="70")
        await check_sample_type_gap_note(project.id, db_session)
        from sqlalchemy import select as _sel
        count = (await db_session.execute(
            _sel(Note).where(Note.entity_id == project.id)
        )).scalars().all()
        assert count == []

    async def test_no_batches_resolves_existing_note(self, db_session: AsyncSession):
        """If a gap note exists but the project now has no batches, note auto-resolves."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="71")
        wa_code = await _seed_wa_code(db_session, code="P-71", level=WACodeLevel.PROJECT)
        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code)

        # Seed a pre-existing gap note manually
        existing = Note(
            entity_type=NoteEntityType.PROJECT,
            entity_id=project.id,
            note_type=NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
            body="stale note",
            is_blocking=True,
            is_resolved=False,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(existing)
        await db_session.flush()

        await check_sample_type_gap_note(project.id, db_session)

        await db_session.refresh(existing)
        assert existing.is_resolved is True

    async def test_batch_with_required_code_present_creates_no_note(
        self, db_session: AsyncSession
    ):
        """When the required WA code is on the WA, no gap note is created."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="72")
        employee = await _seed_employee(db_session)
        role = await _seed_role(db_session, employee)
        entry = await _seed_time_entry(db_session, project, school, employee, role)

        wa_code = await _seed_wa_code(db_session, code="P-72", level=WACodeLevel.PROJECT)
        sample_type = await _seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=wa_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()

        await _seed_batch(db_session, entry, sample_type)

        wa = await _seed_work_auth(db_session, project)
        await _seed_wa_project_code(db_session, wa, wa_code)

        await check_sample_type_gap_note(project.id, db_session)

        from sqlalchemy import select as _sel
        notes = (await db_session.execute(
            _sel(Note).where(
                Note.entity_id == project.id,
                Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
            )
        )).scalars().all()
        assert notes == []

    async def test_batch_with_missing_code_creates_blocking_note(
        self, db_session: AsyncSession
    ):
        """When a required WA code is absent, a blocking system note is created."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="73")
        employee = await _seed_employee(db_session)
        role = await _seed_role(db_session, employee)
        entry = await _seed_time_entry(db_session, project, school, employee, role)

        required_code = await _seed_wa_code(db_session, code="P-73-REQ", level=WACodeLevel.PROJECT)
        sample_type = await _seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=required_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()

        await _seed_batch(db_session, entry, sample_type)

        # WA exists but the required code is NOT on it
        await _seed_work_auth(db_session, project)

        await check_sample_type_gap_note(project.id, db_session)

        from sqlalchemy import select as _sel
        note = (await db_session.execute(
            _sel(Note).where(
                Note.entity_id == project.id,
                Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
                Note.is_resolved.is_(False),
            )
        )).scalar_one()
        assert note.is_blocking is True
        assert "P-73-REQ" in note.body

    async def test_adding_missing_code_auto_resolves_note(self, db_session: AsyncSession):
        """After the missing code is added to the WA, the gap note auto-resolves."""
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school, suffix="74")
        employee = await _seed_employee(db_session)
        role = await _seed_role(db_session, employee)
        entry = await _seed_time_entry(db_session, project, school, employee, role)

        required_code = await _seed_wa_code(db_session, code="P-74-REQ", level=WACodeLevel.PROJECT)
        sample_type = await _seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=required_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()
        await _seed_batch(db_session, entry, sample_type)

        wa = await _seed_work_auth(db_session, project)

        # First call: note is created
        await check_sample_type_gap_note(project.id, db_session)
        from sqlalchemy import select as _sel
        note = (await db_session.execute(
            _sel(Note).where(
                Note.entity_id == project.id,
                Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
                Note.is_resolved.is_(False),
            )
        )).scalar_one()
        assert note.is_blocking is True

        # Now add the required code to the WA
        await _seed_wa_project_code(db_session, wa, required_code)

        # Second call: note should resolve
        await check_sample_type_gap_note(project.id, db_session)
        await db_session.refresh(note)
        assert note.is_resolved is True
