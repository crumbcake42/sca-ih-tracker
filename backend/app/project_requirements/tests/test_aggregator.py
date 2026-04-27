"""
Aggregator equivalence tests for get_unfulfilled_requirements_for_project().

Verification gate: for every fixture project, the aggregator's output count must
equal derive_project_status().outstanding_deliverable_count. If this fails, the
deliverable adapter pattern is wrong — stop before Session B.

Fixtures build projects with mixed SCADeliverableStatus combinations using the
existing seed helpers. Each test receives an isolated db_session that rolls back.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import SCADeliverableStatus, WACodeLevel
from app.project_requirements.aggregator import get_unfulfilled_requirements_for_project
from app.projects.services import _DERIVABLE_SCA_STATUSES, derive_project_status

from tests.seeds import (
    seed_deliverable,
    seed_project,
    seed_project_building_deliverable,
    seed_project_deliverable,
    seed_school,
)

# Statuses that should produce an unfulfilled requirement
_UNFULFILLED = frozenset(_DERIVABLE_SCA_STATUSES)
# Statuses that should be fulfilled (manual terminals)
_FULFILLED = frozenset(SCADeliverableStatus) - _UNFULFILLED


# ---------------------------------------------------------------------------
# Per-row predicate: project-level deliverables
# ---------------------------------------------------------------------------


class TestDeliverableAdapterPredicate:
    @pytest.mark.parametrize("sca_status", list(SCADeliverableStatus))
    async def test_project_deliverable_predicate(
        self, db_session: AsyncSession, sca_status: SCADeliverableStatus
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        deliv = await seed_deliverable(db_session, level=WACodeLevel.PROJECT)
        await seed_project_deliverable(db_session, project, deliv, sca_status=sca_status)

        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)

        if sca_status in _UNFULFILLED:
            assert len(reqs) == 1
            assert reqs[0].requirement_type == "deliverable"
            assert reqs[0].requirement_key == str(deliv.id)
            assert reqs[0].label == deliv.name
            assert reqs[0].is_dismissed is False
            assert reqs[0].is_dismissable is False
        else:
            assert len(reqs) == 0, f"Expected fulfilled for {sca_status}"

    @pytest.mark.parametrize("sca_status", list(SCADeliverableStatus))
    async def test_building_deliverable_predicate(
        self, db_session: AsyncSession, sca_status: SCADeliverableStatus
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        deliv = await seed_deliverable(db_session, level=WACodeLevel.BUILDING)
        await seed_project_building_deliverable(
            db_session, project, deliv, school, sca_status=sca_status
        )

        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)

        if sca_status in _UNFULFILLED:
            assert len(reqs) == 1
            assert reqs[0].requirement_type == "building_deliverable"
            assert reqs[0].requirement_key == f"{deliv.id}:{school.id}"
        else:
            assert len(reqs) == 0, f"Expected fulfilled for {sca_status}"


# ---------------------------------------------------------------------------
# Full equivalence gate
# ---------------------------------------------------------------------------


class TestAggregatorEquivalence:
    async def test_count_matches_derive_project_status(self, db_session: AsyncSession):
        """
        GATE TEST: aggregator count == derive_project_status.outstanding_deliverable_count
        for a project with one deliverable in each SCADeliverableStatus (both levels).

        If this assertion fails, the adapter pattern is wrong. Stop before Session B.
        """
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        # Seed one project-level deliverable per status
        for status in SCADeliverableStatus:
            d = await seed_deliverable(db_session, level=WACodeLevel.PROJECT)
            await seed_project_deliverable(db_session, project, d, sca_status=status)

        # Seed one building-level deliverable per status
        for status in SCADeliverableStatus:
            d = await seed_deliverable(db_session, level=WACodeLevel.BUILDING)
            await seed_project_building_deliverable(
                db_session, project, d, school, sca_status=status
            )

        status_read = await derive_project_status(project.id, db_session)
        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)

        assert len(reqs) == status_read.outstanding_deliverable_count, (
            f"Aggregator returned {len(reqs)} unfulfilled requirements but "
            f"derive_project_status reports {status_read.outstanding_deliverable_count} "
            f"outstanding deliverables. The adapter predicate is diverging from the "
            f"closure-gate predicate — stop before Session B."
        )

    async def test_empty_project_returns_empty(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)
        assert reqs == []

    async def test_all_fulfilled_returns_empty(self, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        for status in _FULFILLED:
            d = await seed_deliverable(db_session, level=WACodeLevel.PROJECT)
            await seed_project_deliverable(db_session, project, d, sca_status=status)

        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)
        assert reqs == []

    async def test_requirement_keys_are_unique_within_project(
        self, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        # Two project-level deliverables, same status
        d1 = await seed_deliverable(db_session, level=WACodeLevel.PROJECT)
        d2 = await seed_deliverable(db_session, level=WACodeLevel.PROJECT)
        await seed_project_deliverable(
            db_session, project, d1, sca_status=SCADeliverableStatus.OUTSTANDING
        )
        await seed_project_deliverable(
            db_session, project, d2, sca_status=SCADeliverableStatus.PENDING_WA
        )

        reqs = await get_unfulfilled_requirements_for_project(project.id, db_session)
        keys = [(r.requirement_type, r.requirement_key) for r in reqs]
        assert len(keys) == len(set(keys)), "Duplicate (type, key) pairs in aggregator output"
