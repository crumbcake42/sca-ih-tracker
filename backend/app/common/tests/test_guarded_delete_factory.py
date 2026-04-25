"""
Tests for create_guarded_delete_router factory (app/common/factories.py).

Uses a throwaway FastAPI app that mounts the factory against the Contractor
model (single ref: ProjectContractorLink). Tests are isolated from Session B's
migration — they exercise the factory directly, not the hand-rolled handlers
still live in app/contractors/router/base.py.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.factories import create_guarded_delete_router
from app.contractors.models import Contractor
from app.database import get_db
from app.projects.models.links import ProjectContractorLink

# ---------------------------------------------------------------------------
# Test app — factory wired to Contractor
# ---------------------------------------------------------------------------

_factory_router = create_guarded_delete_router(
    model=Contractor,
    not_found_detail="Contractor not found",
    path_param_name="contractor_id",
    refs=[
        (ProjectContractorLink, ProjectContractorLink.contractor_id, "project_contractors_links"),
    ],
)

factory_app = FastAPI()
factory_app.include_router(_factory_router, prefix="/contractors")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contractor(**overrides) -> Contractor:
    defaults = dict(
        name="Acme Abatement",
        address="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
    )
    return Contractor(**{**defaults, **overrides})


async def _seed(db: AsyncSession, *contractors: Contractor) -> list[Contractor]:
    for c in contractors:
        db.add(c)
    await db.flush()
    return list(contractors)


# ---------------------------------------------------------------------------
# Per-test client fixture pointing at the factory test app
# ---------------------------------------------------------------------------


@pytest.fixture
async def factory_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    factory_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=factory_app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac
    factory_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /{contractor_id}/connections
# ---------------------------------------------------------------------------


class TestGetConnections:
    async def test_returns_zero_counts_for_clean_entity(
        self, factory_client: AsyncClient, db_session: AsyncSession
    ):
        [c] = await _seed(db_session, _make_contractor())
        resp = await factory_client.get(f"/contractors/{c.id}/connections")
        assert resp.status_code == 200
        assert resp.json() == {"project_contractors_links": 0}

    async def test_reflects_existing_refs(
        self, factory_client: AsyncClient, db_session: AsyncSession
    ):
        from app.common.enums import Boro
        from app.projects.models import Project
        from app.schools.models import School

        [c] = await _seed(db_session, _make_contractor())
        school = School(
            code="K500",
            name="Conn School",
            address="1 Main",
            city=Boro.BROOKLYN,
            state="NY",
            zip_code="11201",
        )
        db_session.add(school)
        await db_session.flush()
        project = Project(name="Conn Project", project_number="26-FCT-C001")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()
        db_session.add(ProjectContractorLink(project_id=project.id, contractor_id=c.id))
        await db_session.flush()

        resp = await factory_client.get(f"/contractors/{c.id}/connections")
        assert resp.status_code == 200
        assert resp.json()["project_contractors_links"] == 1

    async def test_not_found_returns_404(self, factory_client: AsyncClient):
        resp = await factory_client.get("/contractors/9999/connections")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contractor not found"


# ---------------------------------------------------------------------------
# DELETE /{contractor_id}
# ---------------------------------------------------------------------------


class TestDelete:
    async def test_clean_delete_returns_204(
        self, factory_client: AsyncClient, db_session: AsyncSession
    ):
        [c] = await _seed(db_session, _make_contractor())
        resp = await factory_client.delete(f"/contractors/{c.id}")
        assert resp.status_code == 204

    async def test_not_found_returns_404(self, factory_client: AsyncClient):
        resp = await factory_client.delete("/contractors/9999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contractor not found"

    async def test_blocked_returns_409_with_label(
        self, factory_client: AsyncClient, db_session: AsyncSession
    ):
        from app.common.enums import Boro
        from app.projects.models import Project
        from app.schools.models import School

        [c] = await _seed(db_session, _make_contractor())
        school = School(
            code="K501",
            name="Block School",
            address="1 Main",
            city=Boro.BROOKLYN,
            state="NY",
            zip_code="11201",
        )
        db_session.add(school)
        await db_session.flush()
        project = Project(name="Block Project", project_number="26-FCT-C002")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()
        db_session.add(ProjectContractorLink(project_id=project.id, contractor_id=c.id))
        await db_session.flush()

        resp = await factory_client.delete(f"/contractors/{c.id}")
        assert resp.status_code == 409
        assert "project_contractors_links" in resp.json()["detail"]["blocked_by"]


# ---------------------------------------------------------------------------
# OpenAPI schema — ContractorConnections named and typed
# ---------------------------------------------------------------------------


class TestOpenAPISchema:
    def test_connections_schema_is_named_and_present(self):
        schema = factory_app.openapi()
        components = schema.get("components", {}).get("schemas", {})
        assert "ContractorConnections" in components

    def test_connections_schema_fields_are_integers(self):
        schema = factory_app.openapi()
        props = schema["components"]["schemas"]["ContractorConnections"]["properties"]
        assert "project_contractors_links" in props
        assert props["project_contractors_links"]["type"] == "integer"

    def test_connections_route_references_named_schema(self):
        schema = factory_app.openapi()
        paths = schema.get("paths", {})
        connections_path = "/contractors/{contractor_id}/connections"
        assert connections_path in paths
        response_schema = (
            paths[connections_path]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"]
        )
        ref = response_schema.get("$ref", "")
        assert "ContractorConnections" in ref
