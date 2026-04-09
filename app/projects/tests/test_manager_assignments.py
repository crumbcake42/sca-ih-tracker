"""
Integration tests for project manager assignment endpoints.

POST   /projects/{id}/manager/         — assign (or replace) a manager
GET    /projects/{id}/manager/         — get active assignment
GET    /projects/{id}/manager/history  — full assignment history
DELETE /projects/{id}/manager/         — unassign (close active assignment)

Key behaviours under test:
- Happy-path CRUD
- 404 on unknown project or user
- 409 when the same user is already the active manager (overlap prevention)
- Reassignment closes the previous assignment (unassigned_at set) before inserting a new one
- History grows with each assignment; most-recent is first
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import Boro
from app.projects.models import Project
from app.schools.models import School
from app.users.models import Role, User

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_role(db: AsyncSession) -> Role:
    role = Role(id=1, name="staff")
    db.add(role)
    await db.flush()
    return role


async def _seed_user(db: AsyncSession, role: Role, **overrides) -> User:
    n = overrides.pop("n", 1)
    defaults = dict(
        first_name="Test",
        last_name="User",
        username=f"user{n}",
        email=f"user{n}@example.com",
        hashed_password="irrelevant",
        role_id=role.id,
    )
    user = User(**{**defaults, **overrides})
    db.add(user)
    await db.flush()
    return user


async def _seed_school(db: AsyncSession) -> School:
    school = School(
        code="K001",
        name="Test School",
        address="123 Main St",
        city=Boro.BROOKLYN,
        state="NY",
        zip_code="11201",
    )
    db.add(school)
    await db.flush()
    return school


async def _seed_project(db: AsyncSession, school: School) -> Project:
    project = Project(name="Test Project", project_number="26-111-01")
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


# ---------------------------------------------------------------------------
# POST /projects/{id}/manager/
# ---------------------------------------------------------------------------


class TestAssignManager:
    async def test_assign_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        response = await auth_client.post(
            f"/projects/{project.id}/manager",
            json={"user_id": user.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user.id
        assert data["unassigned_at"] is None
        assert "assigned_at" in data

    async def test_assign_missing_project_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        response = await auth_client.post(
            "/projects/9999/manager",
            json={"user_id": user.id},
        )
        assert response.status_code == 404

    async def test_assign_missing_user_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.post(
            f"/projects/{project.id}/manager",
            json={"user_id": 9999},
        )
        assert response.status_code == 404

    async def test_assign_same_user_twice_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Overlap prevention: assigning the already-active manager is a 409."""
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": user.id}
        )
        response = await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": user.id}
        )
        assert response.status_code == 409

    async def test_reassign_closes_previous_assignment(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Reassigning to a different user closes the current assignment."""
        role = await _seed_role(db_session)
        u1 = await _seed_user(db_session, role, n=1)
        u2 = await _seed_user(db_session, role, n=2, username="user2", email="user2@example.com")
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": u1.id}
        )
        response = await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": u2.id}
        )
        assert response.status_code == 201
        assert response.json()["user_id"] == u2.id

        # Active manager is now u2.
        active = await auth_client.get(f"/projects/{project.id}/manager")
        assert active.json()["user_id"] == u2.id

        # History has two entries; u1's record now has unassigned_at set.
        history = await auth_client.get(f"/projects/{project.id}/manager/history")
        assert len(history.json()) == 2
        closed = next(r for r in history.json() if r["user_id"] == u1.id)
        assert closed["unassigned_at"] is not None


# ---------------------------------------------------------------------------
# GET /projects/{id}/manager/
# ---------------------------------------------------------------------------


class TestGetActiveManager:
    async def test_returns_active_assignment(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": user.id}
        )
        response = await auth_client.get(f"/projects/{project.id}/manager")
        assert response.status_code == 200
        assert response.json()["user_id"] == user.id

    async def test_no_manager_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}/manager")
        assert response.status_code == 404

    async def test_missing_project_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/9999/manager")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/manager/history
# ---------------------------------------------------------------------------


class TestGetManagerHistory:
    async def test_empty_history(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.get(f"/projects/{project.id}/manager/history")
        assert response.status_code == 200
        assert response.json() == []

    async def test_history_sorted_newest_first(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        role = await _seed_role(db_session)
        u1 = await _seed_user(db_session, role, n=1)
        u2 = await _seed_user(db_session, role, n=2, username="user2", email="user2@example.com")
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": u1.id}
        )
        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": u2.id}
        )

        response = await auth_client.get(f"/projects/{project.id}/manager/history")
        assert response.status_code == 200
        records = response.json()
        assert len(records) == 2
        # Newest assignment (u2) should be first.
        assert records[0]["user_id"] == u2.id
        assert records[1]["user_id"] == u1.id


# ---------------------------------------------------------------------------
# DELETE /projects/{id}/manager/
# ---------------------------------------------------------------------------


class TestUnassignManager:
    async def test_unassign_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": user.id}
        )
        response = await auth_client.delete(f"/projects/{project.id}/manager")
        assert response.status_code == 204

        # Active manager endpoint should now return 404.
        follow_up = await auth_client.get(f"/projects/{project.id}/manager")
        assert follow_up.status_code == 404

    async def test_unassign_preserves_history_record(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """DELETE closes the assignment (sets unassigned_at) — does not delete the row."""
        role = await _seed_role(db_session)
        user = await _seed_user(db_session, role)
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)

        await auth_client.post(
            f"/projects/{project.id}/manager", json={"user_id": user.id}
        )
        await auth_client.delete(f"/projects/{project.id}/manager")

        history = await auth_client.get(f"/projects/{project.id}/manager/history")
        records = history.json()
        assert len(records) == 1
        assert records[0]["unassigned_at"] is not None

    async def test_unassign_no_manager_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await _seed_school(db_session)
        project = await _seed_project(db_session, school)
        response = await auth_client.delete(f"/projects/{project.id}/manager")
        assert response.status_code == 404
