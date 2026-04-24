from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.contractors.models import Contractor


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
# GET /contractors/
# ---------------------------------------------------------------------------

class TestListContractors:
    async def test_empty_db_returns_empty_list(self, auth_client: AsyncClient):
        response = await auth_client.get("/contractors/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_seeded_contractor(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, _make_contractor())
        response = await auth_client.get("/contractors/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Acme Abatement"

    async def test_ordered_by_name(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            _make_contractor(name="Zebra Corp"),
            _make_contractor(name="Alpha Inc"),
        )
        response = await auth_client.get("/contractors/")
        data = response.json()
        assert data["items"][0]["name"] == "Alpha Inc"
        assert data["items"][1]["name"] == "Zebra Corp"

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/contractors/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /contractors/{id}
# ---------------------------------------------------------------------------

class TestGetContractor:
    async def test_lookup_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        response = await auth_client.get(f"/contractors/{contractor.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Acme Abatement"

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/contractors/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /contractors/
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = dict(
    name="New Contractor LLC",
    address="456 Broadway",
    city="Brooklyn",
    state="NY",
    zip_code="11201",
)


class TestCreateContractor:
    async def test_happy_path_returns_201(self, auth_client: AsyncClient):
        response = await auth_client.post("/contractors/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Contractor LLC"
        assert "id" in data

    async def test_created_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        response = await auth_client.post("/contractors/", json=_VALID_PAYLOAD)
        assert response.status_code == 201
        contractor_id = response.json()["id"]
        result = await db_session.get(Contractor, contractor_id)
        # The test user is a real seeded user — created_by_id should be set.
        assert result and result.created_by_id is not None

    async def test_invalid_state_too_short_returns_422(self, auth_client: AsyncClient):
        payload = {**_VALID_PAYLOAD, "state": "N"}
        response = await auth_client.post("/contractors/", json=payload)
        assert response.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post("/contractors/", json=_VALID_PAYLOAD)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /contractors/{id}
# ---------------------------------------------------------------------------

class TestUpdateContractor:
    async def test_partial_update(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        response = await auth_client.patch(
            f"/contractors/{contractor.id}", json={"city": "Queens"}
        )
        assert response.status_code == 200
        assert response.json()["city"] == "Queens"
        assert response.json()["name"] == "Acme Abatement"  # untouched

    async def test_updated_by_id_stamped(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        await auth_client.patch(
            f"/contractors/{contractor.id}", json={"city": "Queens"}
        )
        await db_session.refresh(contractor)
        assert contractor.updated_by_id is not None

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch("/contractors/9999", json={"city": "Queens"})
        assert response.status_code == 404

    async def test_invalid_state_too_short_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        response = await auth_client.patch(
            f"/contractors/{contractor.id}", json={"state": "N"}
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /contractors/{contractor_id}/connections
# ---------------------------------------------------------------------------


class TestGetContractorConnections:
    async def test_clean_entity_returns_zero_counts(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        response = await auth_client.get(f"/contractors/{contractor.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_contractors_links"] == 0

    async def test_counts_reflect_existing_references(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.common.enums import Boro
        from app.projects.models import Project
        from app.projects.models.links import ProjectContractorLink
        from app.schools.models import School

        [contractor] = await _seed(db_session, _make_contractor())
        school = School(code="K200", name="Conn School", address="1 Main", city=Boro.BROOKLYN, state="NY", zip_code="11201")
        db_session.add(school)
        await db_session.flush()
        project = Project(name="Conn Project", project_number="26-CONN-C001")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()
        db_session.add(ProjectContractorLink(project_id=project.id, contractor_id=contractor.id))
        await db_session.flush()

        response = await auth_client.get(f"/contractors/{contractor.id}/connections")
        assert response.status_code == 200
        assert response.json()["project_contractors_links"] == 1

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/contractors/9999/connections")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /contractors/{contractor_id}
# ---------------------------------------------------------------------------


class TestDeleteContractor:
    async def test_clean_delete_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        [contractor] = await _seed(db_session, _make_contractor())
        response = await auth_client.delete(f"/contractors/{contractor.id}")
        assert response.status_code == 204

    async def test_not_found_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete("/contractors/9999")
        assert response.status_code == 404

    async def test_blocked_by_project_link_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.common.enums import Boro
        from app.projects.models import Project
        from app.projects.models.links import ProjectContractorLink
        from app.schools.models import School

        [contractor] = await _seed(db_session, _make_contractor())
        school = School(code="K201", name="Del School", address="1 Main", city=Boro.BROOKLYN, state="NY", zip_code="11201")
        db_session.add(school)
        await db_session.flush()
        project = Project(name="Del Project", project_number="26-DEL-C001")
        project.schools = [school]
        db_session.add(project)
        await db_session.flush()
        db_session.add(ProjectContractorLink(project_id=project.id, contractor_id=contractor.id))
        await db_session.flush()

        response = await auth_client.delete(f"/contractors/{contractor.id}")
        assert response.status_code == 409
        assert "project_contractors_links" in response.json()["detail"]["blocked_by"]
