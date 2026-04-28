"""
Aggregator integration tests for ContractorPaymentRecord Silo 2.

Verifies that get_unfulfilled_requirements_for_project correctly surfaces and
filters CPR rows based on fulfilled/dismissed state.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.cprs.models import ContractorPaymentRecord
from app.common.requirements import get_unfulfilled_requirements_for_project
from tests.seeds import seed_contractor, seed_project, seed_school


async def _seed_project(db):
    school = await seed_school(db)
    return await seed_project(db, school)


class TestAggregatorSilo2:
    async def test_unfulfilled_cpr_surfaces(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        db_session.add(
            ContractorPaymentRecord(
                project_id=project.id,
                contractor_id=contractor.id,
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        cpr_results = [r for r in results if r.requirement_type == "contractor_payment_record"]
        assert len(cpr_results) == 1

    async def test_fulfilled_cpr_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        db_session.add(
            ContractorPaymentRecord(
                project_id=project.id,
                contractor_id=contractor.id,
                rfp_saved_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        cpr_results = [r for r in results if r.requirement_type == "contractor_payment_record"]
        assert cpr_results == []

    async def test_dismissed_cpr_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        db_session.add(
            ContractorPaymentRecord(
                project_id=project.id,
                contractor_id=contractor.id,
                dismissed_at=datetime(2025, 12, 1),
                dismissal_reason="Not needed",
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        cpr_results = [r for r in results if r.requirement_type == "contractor_payment_record"]
        assert cpr_results == []

    async def test_unfulfilled_shape(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        contractor = await seed_contractor(db_session)

        db_session.add(
            ContractorPaymentRecord(
                project_id=project.id,
                contractor_id=contractor.id,
            )
        )
        await db_session.flush()

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        cpr_results = [r for r in results if r.requirement_type == "contractor_payment_record"]
        assert len(cpr_results) == 1
        item = cpr_results[0]
        assert item.requirement_type == "contractor_payment_record"
        assert item.project_id == project.id
        assert item.is_dismissable is True
        assert item.is_dismissed is False
