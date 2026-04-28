"""
ORM model tests for ContractorPaymentRecord.

Verifies round-trip persistence, partial unique index behavior, and mixin columns.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cprs.models import ContractorPaymentRecord
from tests.seeds import seed_contractor, seed_project, seed_school


async def _seed_project(db):
    school = await seed_school(db)
    return await seed_project(db, school)


class TestContractorPaymentRecordModel:
    async def test_round_trip_insert_and_select(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        record = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(record)
        await db_session.flush()

        fetched = await db_session.get(ContractorPaymentRecord, record.id)
        assert fetched is not None
        assert fetched.project_id == project.id
        assert fetched.contractor_id == contractor.id
        assert fetched.rfp_saved_at is None
        assert fetched.dismissed_at is None

    async def test_audit_mixin_columns_populated(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        record = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(record)
        await db_session.flush()

        fetched = await db_session.get(ContractorPaymentRecord, record.id)
        assert fetched and fetched.created_at is not None
        assert fetched and fetched.updated_at is not None

    async def test_dismissible_mixin_columns_present(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        record = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(record)
        await db_session.flush()

        fetched = await db_session.get(ContractorPaymentRecord, record.id)
        assert fetched and fetched.dismissal_reason is None
        assert fetched and fetched.dismissed_by_id is None
        assert fetched and fetched.dismissed_at is None

    async def test_partial_unique_index_blocks_duplicate_active_rows(
        self, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        r1 = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_partial_unique_index_allows_row_after_dismissal(
        self, db_session: AsyncSession
    ):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        r1 = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
            dismissed_at=datetime(2025, 12, 1),
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = ContractorPaymentRecord(
            project_id=project.id,
            contractor_id=contractor.id,
        )
        db_session.add(r2)
        await db_session.flush()  # should not raise
