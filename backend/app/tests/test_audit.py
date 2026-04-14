"""
Cross-cutting audit infrastructure tests.

- Batch import (CSV upload) sets created_by_id on created records
- System user sentinel: the '!' hash blocks all authentication attempts
"""

import io

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import verify_password
from app.schools.models import School


# ---------------------------------------------------------------------------
# Batch import audit
# ---------------------------------------------------------------------------


class TestBatchImportAudit:
    async def test_csv_import_sets_created_by_id(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        csv_content = (
            "code,name,address,city,state,zip_code\n"
            "Z001,Audit Import School,1 Test Ave,BROOKLYN,NY,11201"
        )
        response = await auth_client.post(
            "/schools/batch/import",
            files={"file": ("schools.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        school = await db_session.get(School, data["created_items"][0]["id"])
        assert school.created_by_id == 1  # fake_user.id from auth_client fixture


# ---------------------------------------------------------------------------
# System user sentinel
# ---------------------------------------------------------------------------


class TestSystemUserSentinel:
    def test_impossible_hash_blocks_authentication(self):
        """The system user's hashed_password='!' is not a valid bcrypt string.
        Any attempt to verify a password against it fails with an exception or
        returns False, ensuring the system user can never log in."""
        try:
            result = verify_password("anything", "!")
        except Exception:
            return  # bcrypt raises ValueError for invalid hash — auth is blocked
        assert not result, "verify_password with '!' sentinel hash must not return True"

    def test_impossible_hash_blocks_empty_password(self):
        """Verify the sentinel blocks even an empty-string password attempt."""
        try:
            result = verify_password("", "!")
        except Exception:
            return
        assert not result
