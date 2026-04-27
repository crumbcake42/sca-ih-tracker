"""
Integration tests for ContractorPaymentRecordHandler.handle_event.

Tests materialize_for_contractor_linked (CONTRACTOR_LINKED) and
cleanup_for_contractor_unlinked (CONTRACTOR_UNLINKED / Decision #6).

Uses real DB sessions — these tests exercise actual SQL inserts and queries.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import RequirementEvent
from app.cprs.models import ContractorPaymentRecord
from app.cprs.service import (
    ContractorPaymentRecordHandler,
    cleanup_for_contractor_unlinked,
    materialize_for_contractor_linked,
)
from tests.seeds import seed_contractor, seed_project, seed_school


async def _seed_project(db):
    school = await seed_school(db)
    return await seed_project(db, school)


class TestMaterializeForContractorLinked:
    async def test_linked_event_creates_row(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        await materialize_for_contractor_linked(project.id, contractor.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ContractorPaymentRecord).where(
                    ContractorPaymentRecord.project_id == project.id,
                    ContractorPaymentRecord.contractor_id == contractor.id,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].is_required is True
        assert rows[0].rfp_saved_at is None
        assert rows[0].dismissed_at is None
        assert rows[0].created_by_id == SYSTEM_USER_ID

    async def test_materialize_is_idempotent(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        await materialize_for_contractor_linked(project.id, contractor.id, db_session)
        await db_session.flush()
        await materialize_for_contractor_linked(project.id, contractor.id, db_session)
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ContractorPaymentRecord).where(
                    ContractorPaymentRecord.project_id == project.id,
                    ContractorPaymentRecord.contractor_id == contractor.id,
                )
            )
        ).scalars().all()
        assert len(rows) == 1

    async def test_handle_event_delegates_contractor_linked(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        await ContractorPaymentRecordHandler.handle_event(
            project.id,
            RequirementEvent.CONTRACTOR_LINKED,
            {"contractor_id": contractor.id},
            db_session,
        )
        await db_session.flush()

        rows = (
            await db_session.execute(
                select(ContractorPaymentRecord).where(
                    ContractorPaymentRecord.project_id == project.id,
                    ContractorPaymentRecord.contractor_id == contractor.id,
                )
            )
        ).scalars().all()
        assert len(rows) == 1


class TestCleanupForContractorUnlinked:
    async def test_pristine_row_is_deleted(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        row = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
            is_required=True,
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_contractor_unlinked(project.id, contractor.id, db_session)
        await db_session.flush()

        assert await db_session.get(ContractorPaymentRecord, row_id) is None

    async def test_rfa_submitted_row_is_kept(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        row = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
            is_required=True,
            rfa_submitted_at=datetime(2025, 11, 15),
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_contractor_unlinked(project.id, contractor.id, db_session)
        await db_session.flush()

        assert await db_session.get(ContractorPaymentRecord, row_id) is not None

    async def test_dismissed_row_is_kept(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        row = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
            is_required=True,
            dismissed_at=datetime(2025, 12, 1),
            dismissal_reason="Not applicable",
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_contractor_unlinked(project.id, contractor.id, db_session)
        await db_session.flush()

        assert await db_session.get(ContractorPaymentRecord, row_id) is not None

    async def test_row_with_file_id_is_kept(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        row = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
            is_required=True,
            file_id=42,
        )
        db_session.add(row)
        await db_session.flush()
        row_id = row.id

        await cleanup_for_contractor_unlinked(project.id, contractor.id, db_session)
        await db_session.flush()

        assert await db_session.get(ContractorPaymentRecord, row_id) is not None

    async def test_no_rows_is_noop(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        # No rows exist — should not raise
        await cleanup_for_contractor_unlinked(project.id, contractor.id, db_session)
        await db_session.flush()
