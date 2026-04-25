"""
API tests for app/notes/router.py and GET /projects/{id}/blocking-issues.

GET    /notes/{entity_type}/{entity_id}   — threaded list
POST   /notes/{entity_type}/{entity_id}   — create user note
POST   /notes/{note_id}/reply             — add reply (reject reply-to-reply)
PATCH  /notes/{note_id}/resolve           — resolve user note (reject system notes)
GET    /projects/{id}/blocking-issues     — aggregated blocking notes
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import Boro, NoteEntityType, NoteType
from app.notes.models import Note
from app.projects.models import Project
from app.schools.models import School

from tests.seeds import seed_school

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_project(
    db: AsyncSession, school: School, number: str = "26-100-0001"
) -> Project:
    project = Project(name="Notes Test Project", project_number=number)
    project.schools = [school]
    db.add(project)
    await db.flush()
    return project


async def _seed_note(
    db: AsyncSession,
    entity_type: NoteEntityType,
    entity_id: int,
    body: str = "Test note",
    *,
    is_blocking: bool = False,
    note_type: NoteType | None = None,
    parent_note_id: int | None = None,
    resolved: bool = False,
) -> Note:
    from datetime import UTC, datetime

    note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        body=body,
        is_blocking=is_blocking,
        note_type=note_type,
        parent_note_id=parent_note_id,
        is_resolved=resolved,
        created_by_id=SYSTEM_USER_ID,
        updated_by_id=SYSTEM_USER_ID,
    )
    if resolved:
        note.resolved_by_id = SYSTEM_USER_ID
        note.resolved_at = datetime.now(tz=UTC)
    db.add(note)
    await db.flush()
    return note


# ---------------------------------------------------------------------------
# GET /notes/{entity_type}/{entity_id}
# ---------------------------------------------------------------------------


class TestListNotes:
    async def test_returns_empty_list_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K010")
        project = await _seed_project(db_session, school, "26-100-0010")

        resp = await client.get(f"/notes/project/{project.id}")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_top_level_notes(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K011")
        project = await _seed_project(db_session, school, "26-100-0011")
        await _seed_note(db_session, NoteEntityType.PROJECT, project.id, "First note")
        await _seed_note(db_session, NoteEntityType.PROJECT, project.id, "Second note")

        resp = await client.get(f"/notes/project/{project.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["body"] == "First note"
        assert data[1]["body"] == "Second note"

    async def test_replies_nested_under_parent(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K012")
        project = await _seed_project(db_session, school, "26-100-0012")
        parent = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Parent"
        )
        await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Reply body",
            parent_note_id=parent.id,
        )

        resp = await client.get(f"/notes/project/{project.id}")

        assert resp.status_code == 200
        data = resp.json()
        # Only one top-level note; reply is nested inside it
        assert len(data) == 1
        assert data[0]["body"] == "Parent"
        assert len(data[0]["replies"]) == 1
        assert data[0]["replies"][0]["body"] == "Reply body"

    async def test_invalid_entity_type_returns_422(self, client: AsyncClient):
        resp = await client.get("/notes/banana/1")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /notes/{entity_type}/{entity_id}
# ---------------------------------------------------------------------------


class TestCreateNote:
    async def test_creates_note_on_existing_entity(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K020")
        project = await _seed_project(db_session, school, "26-100-0020")

        resp = await auth_client.post(
            f"/notes/project/{project.id}",
            json={"body": "Issue found", "is_blocking": True},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == "Issue found"
        assert data["is_blocking"] is True
        assert data["entity_type"] == "project"
        assert data["entity_id"] == project.id
        assert data["note_type"] is None
        assert data["is_resolved"] is False
        assert data["replies"] == []

    async def test_creates_non_blocking_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K021")
        project = await _seed_project(db_session, school, "26-100-0021")

        resp = await auth_client.post(
            f"/notes/project/{project.id}",
            json={"body": "General comment"},
        )

        assert resp.status_code == 201
        assert resp.json()["is_blocking"] is False

    async def test_returns_404_for_nonexistent_entity(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/notes/project/999999",
            json={"body": "This project does not exist"},
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session, code="K022")
        project = await _seed_project(db_session, school, "26-100-0022")

        resp = await client.post(
            f"/notes/project/{project.id}",
            json={"body": "No auth"},
        )
        assert resp.status_code == 401

    async def test_rejects_empty_body(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K023")
        project = await _seed_project(db_session, school, "26-100-0023")

        resp = await auth_client.post(
            f"/notes/project/{project.id}",
            json={"body": ""},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /notes/{note_id}/reply
# ---------------------------------------------------------------------------


class TestCreateReply:
    async def test_creates_reply_on_top_level_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K030")
        project = await _seed_project(db_session, school, "26-100-0030")
        parent = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Parent note"
        )

        resp = await auth_client.post(
            f"/notes/{parent.id}/reply",
            json={"body": "This is a reply"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == "This is a reply"
        assert data["parent_note_id"] == parent.id
        assert data["is_blocking"] is False
        assert data["entity_type"] == "project"
        assert data["entity_id"] == project.id

    async def test_reply_to_reply_is_rejected(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K031")
        project = await _seed_project(db_session, school, "26-100-0031")
        parent = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Parent"
        )
        reply = await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Reply",
            parent_note_id=parent.id,
        )

        resp = await auth_client.post(
            f"/notes/{reply.id}/reply",
            json={"body": "Nested reply attempt"},
        )

        assert resp.status_code == 422
        assert "reply" in resp.json()["detail"].lower()

    async def test_returns_404_for_nonexistent_note(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/notes/999999/reply",
            json={"body": "Parent doesn't exist"},
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session, code="K032")
        project = await _seed_project(db_session, school, "26-100-0032")
        parent = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Parent"
        )

        resp = await client.post(
            f"/notes/{parent.id}/reply",
            json={"body": "No auth"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /notes/{note_id}/resolve
# ---------------------------------------------------------------------------


class TestResolveNote:
    async def test_resolves_user_blocking_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K040")
        project = await _seed_project(db_session, school, "26-100-0040")
        note = await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Blocking issue",
            is_blocking=True,
        )

        resp = await auth_client.patch(
            f"/notes/{note.id}/resolve",
            json={"resolution_note": "Fixed — removed hazardous material"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_resolved"] is True
        assert data["resolved_by_id"] is not None
        assert data["resolved_at"] is not None

    async def test_resolution_note_appended_as_reply(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K041")
        project = await _seed_project(db_session, school, "26-100-0041")
        note = await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Blocking",
            is_blocking=True,
        )

        await auth_client.patch(
            f"/notes/{note.id}/resolve",
            json={"resolution_note": "Resolution rationale"},
        )

        # Fetch the note's replies to verify the resolution note was appended
        list_resp = await auth_client.get(f"/notes/project/{project.id}")
        data = list_resp.json()
        assert len(data) == 1
        assert len(data[0]["replies"]) == 1
        assert data[0]["replies"][0]["body"] == "Resolution rationale"

    async def test_system_note_cannot_be_resolved(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K042")
        project = await _seed_project(db_session, school, "26-100-0042")
        system_note = await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "System-generated conflict note",
            is_blocking=True,
            note_type=NoteType.TIME_ENTRY_CONFLICT,
        )

        resp = await auth_client.patch(
            f"/notes/{system_note.id}/resolve",
            json={"resolution_note": "Trying to resolve system note"},
        )

        assert resp.status_code == 422
        assert "system" in resp.json()["detail"].lower()

    async def test_already_resolved_note_returns_422(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K043")
        project = await _seed_project(db_session, school, "26-100-0043")
        note = await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Already done",
            is_blocking=True,
            resolved=True,
        )

        resp = await auth_client.patch(
            f"/notes/{note.id}/resolve",
            json={"resolution_note": "Re-resolving"},
        )

        assert resp.status_code == 422
        assert "already resolved" in resp.json()["detail"].lower()

    async def test_returns_404_for_nonexistent_note(self, auth_client: AsyncClient):
        resp = await auth_client.patch(
            "/notes/999999/resolve",
            json={"resolution_note": "Note doesn't exist"},
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        school = await seed_school(db_session, code="K044")
        project = await _seed_project(db_session, school, "26-100-0044")
        note = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Blocking", is_blocking=True
        )

        resp = await client.patch(
            f"/notes/{note.id}/resolve",
            json={"resolution_note": "No auth"},
        )
        assert resp.status_code == 401

    async def test_rejects_missing_resolution_note(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K045")
        project = await _seed_project(db_session, school, "26-100-0045")
        note = await _seed_note(
            db_session, NoteEntityType.PROJECT, project.id, "Blocking", is_blocking=True
        )

        resp = await auth_client.patch(
            f"/notes/{note.id}/resolve",
            json={"resolution_note": ""},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{id}/blocking-issues
# ---------------------------------------------------------------------------


class TestGetBlockingIssues:
    async def test_returns_empty_list_when_none(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K050")
        project = await _seed_project(db_session, school, "26-100-0050")

        resp = await auth_client.get(f"/projects/{project.id}/blocking-issues")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_blocking_note_on_project(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K051")
        project = await _seed_project(db_session, school, "26-100-0051")
        await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Site access blocked",
            is_blocking=True,
        )

        resp = await auth_client.get(f"/projects/{project.id}/blocking-issues")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["body"] == "Site access blocked"
        assert data[0]["entity_type"] == "project"
        assert data[0]["entity_id"] == project.id
        assert data[0]["link"] == f"/projects/{project.id}"

    async def test_excludes_resolved_notes(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        school = await seed_school(db_session, code="K052")
        project = await _seed_project(db_session, school, "26-100-0052")
        await _seed_note(
            db_session,
            NoteEntityType.PROJECT,
            project.id,
            "Resolved issue",
            is_blocking=True,
            resolved=True,
        )

        resp = await auth_client.get(f"/projects/{project.id}/blocking-issues")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_404_for_nonexistent_project(self, auth_client: AsyncClient):
        resp = await auth_client.get("/projects/999999/blocking-issues")
        assert resp.status_code == 404
