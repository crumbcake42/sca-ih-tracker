"""
Integration tests for ProjectDocumentHandler.handle_event.

Tests materialize_for_time_entry (TIME_ENTRY_CREATED),
materialize_for_wa_code_added (WA_CODE_ADDED),
and cleanup_for_wa_code_removed (WA_CODE_REMOVED / Decision #6).

Uses real DB sessions — these tests exercise actual SQL inserts and queries.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import DocumentType, EmployeeRoleType, RequirementEvent
from app.project_requirements.models import WACodeRequirementTrigger
from app.project_requirements.services import hash_template_params
from app.required_docs.models import ProjectDocumentRequirement
from app.required_docs.service import (
    ROLES_REQUIRING_DAILY_LOG,
    ProjectDocumentHandler,
    cleanup_for_wa_code_removed,
    materialize_for_time_entry,
    materialize_for_wa_code_added,
)
from tests.seeds import (
    seed_employee,
    seed_employee_role,
    seed_project,
    seed_school,
    seed_time_entry,
    seed_wa_code,
)


async def _seed_project_with_school(db):
    school = await seed_school(db)
    project = await seed_project(db, school)
    return project, school


async def _seed_trigger(db, wa_code, doc_type: DocumentType) -> WACodeRequirementTrigger:
    params = {"document_type": doc_type.value}
    trigger = WACodeRequirementTrigger(
        wa_code_id=wa_code.id,
        requirement_type_name="project_document",
        template_params=params,
        template_params_hash=hash_template_params(params),
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    db.add(trigger)
    await db.flush()
    return trigger


class TestMaterializeForTimeEntry:
    async def test_mapped_role_materializes_daily_log(self, db_session: AsyncSession):
        project, school = await _seed_project_with_school(db_session)
        employee = await seed_employee(db_session)
        role = await seed_employee_role(
            db_session, employee, role_type=EmployeeRoleType.ACM_AIR_TECH
        )
        entry = await seed_time_entry(db_session, employee, role, project, school)

        await materialize_for_time_entry(project.id, entry.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id,
                    ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].employee_id == employee.id
        assert rows[0].date == entry.start_datetime.date()
        assert rows[0].school_id == school.id
        assert rows[0].is_saved is False
        assert rows[0].dismissed_at is None

    async def test_unmapped_role_produces_no_rows(self, db_session: AsyncSession):
        project, school = await _seed_project_with_school(db_session)
        employee = await seed_employee(db_session)
        role = await seed_employee_role(
            db_session, employee, role_type=EmployeeRoleType.ACM_INSPECTOR_A
        )
        entry = await seed_time_entry(db_session, employee, role, project, school)

        await materialize_for_time_entry(project.id, entry.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id
                )
            )
        ).scalars().all()
        assert rows == []

    async def test_dispatch_is_idempotent(self, db_session: AsyncSession):
        project, school = await _seed_project_with_school(db_session)
        employee = await seed_employee(db_session)
        role = await seed_employee_role(
            db_session, employee, role_type=EmployeeRoleType.ACM_AIR_TECH
        )
        entry = await seed_time_entry(db_session, employee, role, project, school)

        await materialize_for_time_entry(project.id, entry.id, db_session)
        await db_session.flush()
        await materialize_for_time_entry(project.id, entry.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id,
                    ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
                )
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_handle_event_delegates_time_entry_created(self, db_session: AsyncSession):
        project, school = await _seed_project_with_school(db_session)
        employee = await seed_employee(db_session)
        role = await seed_employee_role(
            db_session, employee, role_type=EmployeeRoleType.ACM_PROJECT_MONITOR
        )
        entry = await seed_time_entry(db_session, employee, role, project, school)

        await ProjectDocumentHandler.handle_event(
            project.id,
            RequirementEvent.TIME_ENTRY_CREATED,
            {"time_entry_id": entry.id},
            db_session,
        )
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id,
                    ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
                )
            )
        ).scalars().all()
        assert len(rows) == 1


class TestMaterializeForWaCodeAdded:
    async def test_trigger_materializes_reoccupancy_letter(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code, DocumentType.REOCCUPANCY_LETTER)

        await materialize_for_wa_code_added(project.id, wa_code.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id,
                    ProjectDocumentRequirement.document_type == DocumentType.REOCCUPANCY_LETTER,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].wa_code_trigger_id == trigger.id

    async def test_wa_code_added_idempotent(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        await _seed_trigger(db_session, wa_code, DocumentType.MINOR_LETTER)

        await materialize_for_wa_code_added(project.id, wa_code.id, db_session)
        await db_session.flush()
        await materialize_for_wa_code_added(project.id, wa_code.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id,
                    ProjectDocumentRequirement.document_type == DocumentType.MINOR_LETTER,
                )
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_wa_code_with_no_project_document_trigger_is_noop(
        self, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        # Register a trigger for a different requirement type
        params = {"foo": "bar"}
        other_trigger = WACodeRequirementTrigger(
            wa_code_id=wa_code.id,
            requirement_type_name="deliverable",
            template_params=params,
            template_params_hash=hash_template_params(params),
            created_by_id=SYSTEM_USER_ID,
            updated_by_id=SYSTEM_USER_ID,
        )
        db_session.add(other_trigger)
        await db_session.flush()

        await materialize_for_wa_code_added(project.id, wa_code.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ProjectDocumentRequirement).where(
                    ProjectDocumentRequirement.project_id == project.id
                )
            )
        ).scalars().all()
        assert rows == []


class TestCleanupForWaCodeRemoved:
    async def test_pristine_row_is_deleted(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code, DocumentType.REOCCUPANCY_LETTER)

        row = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.REOCCUPANCY_LETTER,
            is_required=True,
            is_saved=False,
            wa_code_trigger_id=trigger.id,
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_wa_code_removed(project.id, wa_code.id, db_session)
        await db_session.flush()

        assert await db_session.get(ProjectDocumentRequirement, row_id) is None

    async def test_saved_row_is_kept(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code, DocumentType.REOCCUPANCY_LETTER)

        row = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.REOCCUPANCY_LETTER,
            is_required=True,
            is_saved=True,
            wa_code_trigger_id=trigger.id,
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_wa_code_removed(project.id, wa_code.id, db_session)
        await db_session.flush()

        assert await db_session.get(ProjectDocumentRequirement, row_id) is not None

    async def test_dismissed_row_is_kept(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code, DocumentType.REOCCUPANCY_LETTER)

        row = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.REOCCUPANCY_LETTER,
            is_required=True,
            is_saved=False,
            wa_code_trigger_id=trigger.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_wa_code_removed(project.id, wa_code.id, db_session)
        await db_session.flush()

        assert await db_session.get(ProjectDocumentRequirement, row_id) is not None

    async def test_row_with_file_id_is_kept(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)
        trigger = await _seed_trigger(db_session, wa_code, DocumentType.MINOR_LETTER)

        row = ProjectDocumentRequirement(
            project_id=project.id,
            document_type=DocumentType.MINOR_LETTER,
            is_required=True,
            is_saved=False,
            wa_code_trigger_id=trigger.id,
            file_id=99,
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_wa_code_removed(project.id, wa_code.id, db_session)
        await db_session.flush()

        assert await db_session.get(ProjectDocumentRequirement, row_id) is not None

    async def test_no_triggers_for_removed_wa_code_is_noop(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        wa_code = await seed_wa_code(db_session)

        # No triggers exist for this WA code — should not raise
        await cleanup_for_wa_code_removed(project.id, wa_code.id, db_session)
        await db_session.flush()
