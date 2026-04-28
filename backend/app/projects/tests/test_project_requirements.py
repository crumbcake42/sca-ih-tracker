"""
Endpoint tests for GET /projects/{id}/requirements.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import DocumentType
from app.required_docs.models import ProjectDocumentRequirement
from tests.seeds import seed_contractor, seed_project, seed_school


class TestListProjectRequirements:
    async def test_empty_project_returns_empty_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        response = await auth_client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_unfulfilled_doc_requirement(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        db_session.add(
            ProjectDocumentRequirement(
                project_id=project.id,
                document_type=DocumentType.REOCCUPANCY_LETTER,
                is_saved=False,
            )
        )
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["requirement_type"] == "project_document"
        assert body[0]["project_id"] == project.id
        assert body[0]["is_dismissed"] is False
        assert body[0]["is_dismissable"] is True

    async def test_returns_unfulfilled_cpr(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.cprs.models import ContractorPaymentRecord

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        contractor = await seed_contractor(db_session)
        db_session.add(
            ContractorPaymentRecord(project_id=project.id, contractor_id=contractor.id)
        )
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 200
        body = response.json()
        cpr_items = [r for r in body if r["requirement_type"] == "contractor_payment_record"]
        assert len(cpr_items) == 1

    async def test_returns_multiple_across_silos(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.cprs.models import ContractorPaymentRecord

        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        contractor = await seed_contractor(db_session)
        db_session.add(
            ContractorPaymentRecord(project_id=project.id, contractor_id=contractor.id)
        )
        db_session.add(
            ProjectDocumentRequirement(
                project_id=project.id,
                document_type=DocumentType.REOCCUPANCY_LETTER,
                is_saved=False,
            )
        )
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_saved_requirement_does_not_surface(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)
        db_session.add(
            ProjectDocumentRequirement(
                project_id=project.id,
                document_type=DocumentType.REOCCUPANCY_LETTER,
                is_saved=True,
            )
        )
        await db_session.flush()

        response = await auth_client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 200
        assert response.json() == []

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session)
        project = await seed_project(db_session, school)

        response = await client.get(f"/projects/{project.id}/requirements")

        assert response.status_code == 401
