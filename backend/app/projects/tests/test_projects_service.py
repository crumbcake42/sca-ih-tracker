"""
Unit tests for project services in app/projects/services.py.

Tests call service functions directly against db_session; no HTTP.
All tests roll back via the conftest transaction fixture.
"""

# from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import (
    Boro,
    NoteEntityType,
    NoteType,
    ProjectStatus,
    SCADeliverableStatus,
    TimeEntryStatus,
    WACodeLevel,
    WACodeStatus,
)
from app.deliverables.models import (
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.lab_results.models import SampleTypeWACode
from app.notes.models import Note
from app.projects.services import (
    check_sample_type_gap_note,
    derive_project_status,
    ensure_deliverables_exist,
    get_blocking_notes_for_project,
    recalculate_deliverable_sca_status,
)
from app.schools.models import School

from tests.seeds import (
    seed_employee,
    seed_school,
    seed_project,
    seed_work_auth,
    seed_wa_code,
    seed_work_auth_project_code,
    seed_work_auth_building_code,
    seed_employee_role,
    seed_time_entry,
    seed_sample_type,
    seed_sample_batch,
    seed_deliverable,
    seed_deliverable_with_trigger,
    seed_project_deliverable,
    seed_project_building_deliverable,
    seed_blocking_note,
)

# if TYPE_CHECKING:
#     from app.time_entries.models import TimeEntry

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetBlockingNotesForProject:
    async def test_empty_returns_empty_list(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0000")

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result == []

    async def test_returns_project_level_note(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0002")

        await seed_blocking_note(
            db_session,
            entity_type=NoteEntityType.PROJECT,
            entity_id=project.id,
            body="Project issue",
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.PROJECT
        assert result[0].entity_id == project.id
        assert result[0].body == "Project issue"
        assert result[0].link == f"/projects/{project.id}"

    async def test_returns_time_entry_note(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0003")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.TIME_ENTRY, entity_id=entry.id
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.TIME_ENTRY
        assert result[0].entity_id == entry.id
        assert result[0].link == f"/time-entries/{entry.id}"

    async def test_returns_sample_batch_note(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0004")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        st = await seed_sample_type(db_session)
        batch = await seed_sample_batch(db_session, entry, st)

        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.SAMPLE_BATCH, entity_id=batch.id
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.SAMPLE_BATCH
        assert result[0].entity_id == batch.id
        assert result[0].link == f"/lab-results/batches/{batch.id}"

    async def test_returns_deliverable_note(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0005")
        deliv = await seed_deliverable(db_session)
        await seed_project_deliverable(db_session, project, deliv)

        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.DELIVERABLE, entity_id=deliv.id
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 1
        assert result[0].entity_type == NoteEntityType.DELIVERABLE
        assert result[0].entity_id == deliv.id
        assert result[0].link == f"/deliverables/{deliv.id}"

    async def test_excludes_resolved_notes(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0006")

        await seed_blocking_note(
            db_session,
            entity_type=NoteEntityType.PROJECT,
            entity_id=project.id,
            is_resolved=True,
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result == []

    async def test_excludes_other_projects_time_entry(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project_a = await seed_project(db_session, school, project_number="26-666-0007")
        project_b = await seed_project(db_session, school, project_number="26-666-0008")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)

        # Time entry belongs to project_b, not project_a
        entry_b = await seed_time_entry(db_session, emp, role, project_b, school)
        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.TIME_ENTRY, entity_id=entry_b.id
        )

        result = await get_blocking_notes_for_project(project_a.id, db_session)

        assert result == []

    async def test_ordered_by_created_at(self, db_session: AsyncSession):
        """Notes are returned in ascending created_at order."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0009")

        # Insert three notes on the project; DB will assign ascending created_at
        for body in ("First", "Second", "Third"):
            await seed_blocking_note(
                db_session,
                entity_type=NoteEntityType.PROJECT,
                entity_id=project.id,
                body=body,
            )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert len(result) == 3
        assert result[0].body == "First"
        assert result[1].body == "Second"
        assert result[2].body == "Third"

    async def test_entity_label_format(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0010")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)

        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.TIME_ENTRY, entity_id=entry.id
        )

        result = await get_blocking_notes_for_project(project.id, db_session)

        assert result[0].entity_label == f"Time Entry #{entry.id}"


# ---------------------------------------------------------------------------
# Tests: recalculate_deliverable_sca_status
# ---------------------------------------------------------------------------


class TestRecalculateDeliverableSCAStatus:
    async def test_no_wa_sets_all_derivable_to_pending_wa(
        self, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0020")
        wa_code = await seed_wa_code(db_session, code="A-20", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 20", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        # Start at OUTSTANDING; no WA on the project
        pd = await seed_project_deliverable(
            db_session, project, deliv, sca_status=SCADeliverableStatus.OUTSTANDING
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

    async def test_active_code_sets_outstanding(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0021")
        wa_code = await seed_wa_code(db_session, code="A-21", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 21", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.ACTIVE
        )
        pd = await seed_project_deliverable(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_added_by_rfa_code_sets_outstanding(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0022")
        wa_code = await seed_wa_code(db_session, code="A-22", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 22", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.ADDED_BY_RFA
        )
        pd = await seed_project_deliverable(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_rfa_needed_code_sets_pending_rfa(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0023")
        wa_code = await seed_wa_code(db_session, code="A-23", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 23", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.RFA_NEEDED
        )
        pd = await seed_project_deliverable(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_rfa_pending_code_sets_pending_rfa(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0024")
        wa_code = await seed_wa_code(db_session, code="A-24", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 24", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.RFA_PENDING
        )
        pd = await seed_project_deliverable(db_session, project, deliv)

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_removed_code_treated_as_absent(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0025")
        wa_code = await seed_wa_code(db_session, code="A-25", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 25", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.REMOVED
        )
        pd = await seed_project_deliverable(
            db_session, project, deliv, sca_status=SCADeliverableStatus.OUTSTANDING
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)

        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

    async def test_manual_statuses_untouched(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0026")
        wa_code = await seed_wa_code(db_session, code="A-26", level=WACodeLevel.PROJECT)
        deliv_a = await seed_deliverable_with_trigger(
            db_session, name="Deliv 26a", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        deliv_b = await seed_deliverable_with_trigger(
            db_session, name="Deliv 26b", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        deliv_c = await seed_deliverable_with_trigger(
            db_session, name="Deliv 26c", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.ACTIVE
        )

        pd_ur = await seed_project_deliverable(
            db_session, project, deliv_a, sca_status=SCADeliverableStatus.UNDER_REVIEW
        )
        pd_rej = await seed_project_deliverable(
            db_session, project, deliv_b, sca_status=SCADeliverableStatus.REJECTED
        )
        pd_app = await seed_project_deliverable(
            db_session, project, deliv_c, sca_status=SCADeliverableStatus.APPROVED
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd_ur)
        await db_session.refresh(pd_rej)
        await db_session.refresh(pd_app)

        assert pd_ur.sca_status == SCADeliverableStatus.UNDER_REVIEW
        assert pd_rej.sca_status == SCADeliverableStatus.REJECTED
        assert pd_app.sca_status == SCADeliverableStatus.APPROVED

    async def test_building_level_deliverable_updated(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0027")
        wa_code = await seed_wa_code(
            db_session, code="B-27", level=WACodeLevel.BUILDING
        )
        deliv = await seed_deliverable_with_trigger(
            db_session,
            name="Bldg Deliv 27",
            level=WACodeLevel.BUILDING,
            wa_code=wa_code,
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_building_code(
            db_session, wa, wa_code, project, school, status=WACodeStatus.ACTIVE
        )
        pbd = await seed_project_building_deliverable(
            db_session, project, deliv, school
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pbd)

        assert pbd.sca_status == SCADeliverableStatus.OUTSTANDING

    async def test_building_level_rfa_needed_sets_pending_rfa(
        self, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0028")
        wa_code = await seed_wa_code(
            db_session, code="B-28", level=WACodeLevel.BUILDING
        )
        deliv = await seed_deliverable_with_trigger(
            db_session,
            name="Bldg Deliv 28",
            level=WACodeLevel.BUILDING,
            wa_code=wa_code,
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_building_code(
            db_session, wa, wa_code, project, school, status=WACodeStatus.RFA_NEEDED
        )
        pbd = await seed_project_building_deliverable(
            db_session, project, deliv, school
        )

        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pbd)

        assert pbd.sca_status == SCADeliverableStatus.PENDING_RFA

    async def test_status_promotion_chain(self, db_session: AsyncSession):
        """Verify pending_wa → pending_rfa → outstanding promotion sequence."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0029")
        wa_code = await seed_wa_code(db_session, code="A-29", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 29", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        pd = await seed_project_deliverable(db_session, project, deliv)

        # Stage 1: no WA → pending_wa (already the default)
        await recalculate_deliverable_sca_status(project.id, db_session)
        await db_session.refresh(pd)
        assert pd.sca_status == SCADeliverableStatus.PENDING_WA

        # Stage 2: WA added with rfa_needed code → pending_rfa
        wa = await seed_work_auth(db_session, project)
        pc = await seed_work_auth_project_code(
            db_session, wa, wa_code, status=WACodeStatus.RFA_NEEDED
        )
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
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0030")
        wa_code = await seed_wa_code(db_session, code="A-30", level=WACodeLevel.PROJECT)
        await seed_deliverable_with_trigger(
            db_session, name="Deliv 30", level=WACodeLevel.PROJECT, wa_code=wa_code
        )

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        result = (
            (
                await db_session.execute(
                    _select(ProjectDeliverable).where(
                        ProjectDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert result == []

    async def test_creates_project_level_deliverable(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0031")
        wa_code = await seed_wa_code(db_session, code="A-31", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 31", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        rows = (
            (
                await db_session.execute(
                    _select(ProjectDeliverable).where(
                        ProjectDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].deliverable_id == deliv.id

    async def test_creates_building_level_deliverable(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0032")
        wa_code = await seed_wa_code(
            db_session, code="B-32", level=WACodeLevel.BUILDING
        )
        deliv = await seed_deliverable_with_trigger(
            db_session,
            name="Bldg Deliv 32",
            level=WACodeLevel.BUILDING,
            wa_code=wa_code,
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_building_code(db_session, wa, wa_code, project, school)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        rows = (
            (
                await db_session.execute(
                    _select(ProjectBuildingDeliverable).where(
                        ProjectBuildingDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].deliverable_id == deliv.id
        assert rows[0].school_id == school.id

    async def test_idempotent(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0033")
        wa_code = await seed_wa_code(db_session, code="A-33", level=WACodeLevel.PROJECT)
        await seed_deliverable_with_trigger(
            db_session, name="Deliv 33", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)
        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        rows = (
            (
                await db_session.execute(
                    _select(ProjectDeliverable).where(
                        ProjectDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    async def test_does_not_create_project_deliv_for_building_code(
        self, db_session: AsyncSession
    ):
        """A building-level code should not produce a project-level deliverable."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0034")
        bldg_code = await seed_wa_code(
            db_session, code="B-34", level=WACodeLevel.BUILDING
        )
        await seed_deliverable_with_trigger(
            db_session,
            name="Bldg Deliv 34",
            level=WACodeLevel.BUILDING,
            wa_code=bldg_code,
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_building_code(db_session, wa, bldg_code, project, school)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        proj_rows = (
            (
                await db_session.execute(
                    _select(ProjectDeliverable).where(
                        ProjectDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert proj_rows == []

    async def test_no_trigger_creates_nothing(self, db_session: AsyncSession):
        """A WA code with no deliverable trigger produces no rows."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0035")
        wa_code = await seed_wa_code(db_session, code="A-35", level=WACodeLevel.PROJECT)
        # No DeliverableWACodeTrigger created
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(db_session, wa, wa_code)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        rows = (
            (
                await db_session.execute(
                    _select(ProjectDeliverable).where(
                        ProjectDeliverable.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert rows == []

    async def test_building_deliv_created_per_school(self, db_session: AsyncSession):
        """Building-level deliverable creates one row per linked school."""
        school_a = await seed_school(db_session)
        project = await seed_project(db_session, school_a, project_number="26-666-0036")
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

        wa_code = await seed_wa_code(
            db_session, code="B-36", level=WACodeLevel.BUILDING
        )
        deliv = await seed_deliverable_with_trigger(
            db_session,
            name="Bldg Deliv 36",
            level=WACodeLevel.BUILDING,
            wa_code=wa_code,
        )
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_building_code(db_session, wa, wa_code, project, school_a)
        await seed_work_auth_building_code(db_session, wa, wa_code, project, school_b)

        await ensure_deliverables_exist(project.id, db_session)

        from sqlalchemy import select as _select

        rows = (
            (
                await db_session.execute(
                    _select(ProjectBuildingDeliverable).where(
                        ProjectBuildingDeliverable.project_id == project.id,
                        ProjectBuildingDeliverable.deliverable_id == deliv.id,
                    )
                )
            )
            .scalars()
            .all()
        )
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
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0070")
        await check_sample_type_gap_note(project.id, db_session)
        from sqlalchemy import select as _sel

        count = (
            (await db_session.execute(_sel(Note).where(Note.entity_id == project.id)))
            .scalars()
            .all()
        )
        assert count == []

    async def test_no_batches_resolves_existing_note(self, db_session: AsyncSession):
        """If a gap note exists but the project now has no batches, note auto-resolves."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0071")
        wa_code = await seed_wa_code(db_session, code="P-71", level=WACodeLevel.PROJECT)
        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(db_session, wa, wa_code)

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
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0072")
        employee = await seed_employee(db_session)
        role = await seed_employee_role(db_session, employee)
        entry = await seed_time_entry(db_session, employee, role, project, school)

        wa_code = await seed_wa_code(db_session, code="P-72", level=WACodeLevel.PROJECT)
        sample_type = await seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=wa_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()

        await seed_sample_batch(db_session, entry, sample_type)

        wa = await seed_work_auth(db_session, project)
        await seed_work_auth_project_code(db_session, wa, wa_code)

        await check_sample_type_gap_note(project.id, db_session)

        from sqlalchemy import select as _sel

        notes = (
            (
                await db_session.execute(
                    _sel(Note).where(
                        Note.entity_id == project.id,
                        Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert notes == []

    async def test_batch_with_missing_code_creates_blocking_note(
        self, db_session: AsyncSession
    ):
        """When a required WA code is absent, a blocking system note is created."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0073")
        employee = await seed_employee(db_session)
        role = await seed_employee_role(db_session, employee)
        entry = await seed_time_entry(db_session, employee, role, project, school)

        required_code = await seed_wa_code(
            db_session, code="P-73-REQ", level=WACodeLevel.PROJECT
        )
        sample_type = await seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=required_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()

        await seed_sample_batch(db_session, entry, sample_type)

        # WA exists but the required code is NOT on it
        await seed_work_auth(db_session, project)

        await check_sample_type_gap_note(project.id, db_session)

        from sqlalchemy import select as _sel

        note = (
            await db_session.execute(
                _sel(Note).where(
                    Note.entity_id == project.id,
                    Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
                    Note.is_resolved.is_(False),
                )
            )
        ).scalar_one()
        assert note.is_blocking is True
        assert "P-73-REQ" in note.body

    async def test_adding_missing_code_auto_resolves_note(
        self, db_session: AsyncSession
    ):
        """After the missing code is added to the WA, the gap note auto-resolves."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0074")
        employee = await seed_employee(db_session)
        role = await seed_employee_role(db_session, employee)
        entry = await seed_time_entry(db_session, employee, role, project, school)

        required_code = await seed_wa_code(
            db_session, code="P-74-REQ", level=WACodeLevel.PROJECT
        )
        sample_type = await seed_sample_type(db_session)
        link = SampleTypeWACode(
            sample_type_id=sample_type.id,
            wa_code_id=required_code.id,
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(link)
        await db_session.flush()
        await seed_sample_batch(db_session, entry, sample_type)

        wa = await seed_work_auth(db_session, project)

        # First call: note is created
        await check_sample_type_gap_note(project.id, db_session)
        from sqlalchemy import select as _sel

        note = (
            await db_session.execute(
                _sel(Note).where(
                    Note.entity_id == project.id,
                    Note.note_type == NoteType.MISSING_SAMPLE_TYPE_WA_CODE,
                    Note.is_resolved.is_(False),
                )
            )
        ).scalar_one()
        assert note.is_blocking is True

        # Now add the required code to the WA
        await seed_work_auth_project_code(db_session, wa, required_code)

        # Second call: note should resolve
        await check_sample_type_gap_note(project.id, db_session)
        await db_session.refresh(note)
        assert note.is_resolved is True


# ---------------------------------------------------------------------------
# Tests: derive_project_status
# ---------------------------------------------------------------------------


class TestDeriveProjectStatus:
    async def test_no_time_entries_returns_setup(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0080")

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.SETUP
        assert result.has_work_auth is False
        assert result.blocking_issues == []

    async def test_blocking_note_returns_blocked(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0081")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        await seed_time_entry(db_session, emp, role, project, school)
        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.PROJECT, entity_id=project.id
        )

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.BLOCKED
        assert len(result.blocking_issues) == 1

    async def test_blocking_note_overrides_setup(self, db_session: AsyncSession):
        """BLOCKED takes priority even when no time entries exist."""
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0082")
        await seed_blocking_note(
            db_session, entity_type=NoteEntityType.PROJECT, entity_id=project.id
        )

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.BLOCKED

    async def test_outstanding_deliverable_returns_in_progress(
        self, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0083")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        # Flip the entry to ENTERED so it's not unconfirmed
        entry.status = TimeEntryStatus.ENTERED
        await db_session.flush()
        wa_code = await seed_wa_code(db_session, code="A-83", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 83", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        await seed_project_deliverable(
            db_session, project, deliv, sca_status=SCADeliverableStatus.OUTSTANDING
        )

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.IN_PROGRESS
        assert result.outstanding_deliverable_count == 1

    async def test_assumed_time_entry_returns_in_progress(
        self, db_session: AsyncSession
    ):
        """Unconfirmed (assumed) time entries block READY_TO_CLOSE."""
        from app.common.enums import TimeEntryStatus

        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0084")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        entry.status = TimeEntryStatus.ASSUMED
        await db_session.flush()

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.IN_PROGRESS
        assert result.unconfirmed_time_entry_count == 1

    async def test_all_clear_returns_ready_to_close(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0085")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        entry.status = TimeEntryStatus.ENTERED
        await db_session.flush()
        # Deliverable exists but is approved (not outstanding)
        wa_code = await seed_wa_code(db_session, code="A-85", level=WACodeLevel.PROJECT)
        deliv = await seed_deliverable_with_trigger(
            db_session, name="Deliv 85", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        await seed_project_deliverable(
            db_session, project, deliv, sca_status=SCADeliverableStatus.APPROVED
        )

        result = await derive_project_status(project.id, db_session)

        assert result.status == ProjectStatus.READY_TO_CLOSE
        assert result.outstanding_deliverable_count == 0
        assert result.unconfirmed_time_entry_count == 0
        assert result.pending_rfa_count == 0

    async def test_counts_are_accurate(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0086")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        await seed_time_entry(db_session, emp, role, project, school)
        wa_code = await seed_wa_code(db_session, code="A-86", level=WACodeLevel.PROJECT)
        deliv_a = await seed_deliverable_with_trigger(
            db_session, name="Deliv 86a", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        deliv_b = await seed_deliverable_with_trigger(
            db_session, name="Deliv 86b", level=WACodeLevel.PROJECT, wa_code=wa_code
        )
        await seed_project_deliverable(
            db_session, project, deliv_a, sca_status=SCADeliverableStatus.OUTSTANDING
        )
        await seed_project_deliverable(
            db_session, project, deliv_b, sca_status=SCADeliverableStatus.APPROVED
        )

        result = await derive_project_status(project.id, db_session)

        from app.common.enums import TimeEntryStatus
        from app.time_entries.models import TimeEntry as TE
        from sqlalchemy import select as _sel

        te = (
            await db_session.execute(_sel(TE).where(TE.project_id == project.id))
        ).scalar_one()
        te.status = TimeEntryStatus.ASSUMED
        await db_session.flush()

        result2 = await derive_project_status(project.id, db_session)
        assert result2.outstanding_deliverable_count == 1
        assert result2.unconfirmed_time_entry_count == 1

    async def test_has_work_auth_flag(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school, project_number="26-666-0087")
        emp = await seed_employee(db_session)
        role = await seed_employee_role(db_session, emp)
        entry = await seed_time_entry(db_session, emp, role, project, school)
        entry.status = TimeEntryStatus.ENTERED
        await db_session.flush()

        result_before = await derive_project_status(project.id, db_session)
        assert result_before.has_work_auth is False

        await seed_work_auth(db_session, project)

        result_after = await derive_project_status(project.id, db_session)
        assert result_after.has_work_auth is True
