"""
Aggregator integration tests for Silo 1.

Verifies that unfulfilled, undismissed document requirement rows surface through
get_unfulfilled_requirements_for_project, and that saved or dismissed rows do not.
"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.common.requirements import get_unfulfilled_requirements_for_project
from app.required_docs.models import ProjectDocumentRequirement
from tests.seeds import seed_project, seed_school


async def _seed_project(db):
    school = await seed_school(db)
    return await seed_project(db, school)


async def _seed_req(db, project_id, **overrides):
    defaults = dict(
        project_id=project_id,
        document_type=DocumentType.REOCCUPANCY_LETTER,
        is_saved=False,
    )
    defaults.update(overrides)
    req = ProjectDocumentRequirement(**defaults)
    db.add(req)
    await db.flush()
    return req


class TestAggregatorSilo1:
    async def test_unfulfilled_row_surfaces(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id)

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        doc_reqs = [r for r in results if r.requirement_type == "project_document"]
        assert len(doc_reqs) == 1
        assert doc_reqs[0].project_id == project.id

    async def test_saved_row_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        await _seed_req(db_session, project.id, is_saved=True)

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        doc_reqs = [r for r in results if r.requirement_type == "project_document"]
        assert doc_reqs == []

    async def test_dismissed_row_does_not_surface(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        await _seed_req(
            db_session,
            project.id,
            dismissed_at=datetime(2025, 12, 1),
            dismissal_reason="Not needed",
        )

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        doc_reqs = [r for r in results if r.requirement_type == "project_document"]
        assert doc_reqs == []

    async def test_unfulfilled_requirement_has_correct_shape(self, db_session: AsyncSession):
        project = await _seed_project(db_session)
        await _seed_req(
            db_session, project.id, document_type=DocumentType.MINOR_LETTER
        )

        results = await get_unfulfilled_requirements_for_project(project.id, db_session)
        doc_reqs = [r for r in results if r.requirement_type == "project_document"]
        assert len(doc_reqs) == 1
        req = doc_reqs[0]
        assert req.requirement_type == "project_document"
        assert req.is_dismissable is True
        assert req.is_dismissed is False
        assert req.label == "Minor Letter"
