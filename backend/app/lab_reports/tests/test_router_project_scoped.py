"""
Router tests for GET /projects/{id}/lab-reports.
"""

from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.lab_reports.models import LabReportRequirement
from tests.seeds import (
    seed_employee,
    seed_employee_role,
    seed_project,
    seed_sample_batch,
    seed_sample_type,
    seed_school,
    seed_time_entry,
)


async def _seed_context(db: AsyncSession):
    school = await seed_school(db)
    project = await seed_project(db, school)
    emp = await seed_employee(db)
    role = await seed_employee_role(db, emp)
    entry = await seed_time_entry(db, emp, role, project, school)
    sample_type = await seed_sample_type(db)
    return school, project, entry, sample_type


class TestListLabReportsForProject:
    async def test_returns_active_rows(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(db_session, entry, sample_type)
        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        )
        await db_session.flush()

        resp = await auth_client.get(f"/projects/{project.id}/lab-reports")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_dismissed_hidden_by_default(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, project, entry, sample_type = await _seed_context(db_session)
        batch_a = await seed_sample_batch(db_session, entry, sample_type, batch_num="PSCL-A001")
        batch_b = await seed_sample_batch(db_session, entry, sample_type, batch_num="PSCL-B001")

        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch_a.id)
        )
        db_session.add(
            LabReportRequirement(
                project_id=project.id,
                sample_batch_id=batch_b.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        resp = await auth_client.get(f"/projects/{project.id}/lab-reports")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_include_dismissed_shows_all(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, project, entry, sample_type = await _seed_context(db_session)
        batch_a = await seed_sample_batch(db_session, entry, sample_type, batch_num="PSCL-C001")
        batch_b = await seed_sample_batch(db_session, entry, sample_type, batch_num="PSCL-D001")

        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch_a.id)
        )
        db_session.add(
            LabReportRequirement(
                project_id=project.id,
                sample_batch_id=batch_b.id,
                dismissed_at=datetime(2025, 12, 1),
            )
        )
        await db_session.flush()

        resp = await auth_client.get(
            f"/projects/{project.id}/lab-reports?include_dismissed=true"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_response_includes_label(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        _, project, entry, sample_type = await _seed_context(db_session)
        batch = await seed_sample_batch(
            db_session, entry, sample_type, batch_num="LBL-BATCH-001"
        )
        db_session.add(
            LabReportRequirement(project_id=project.id, sample_batch_id=batch.id)
        )
        await db_session.flush()

        resp = await auth_client.get(f"/projects/{project.id}/lab-reports")
        assert resp.status_code == 200
        assert resp.json()[0]["label"] == "LBL-BATCH-001"

    async def test_404_unknown_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await auth_client.get("/projects/99999/lab-reports")
        assert resp.status_code == 404
