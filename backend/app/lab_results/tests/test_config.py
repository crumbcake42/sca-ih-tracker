"""
Integration tests for lab results config endpoints.

GET    /lab-results/config/sample-types
POST   /lab-results/config/sample-types
GET    /lab-results/config/sample-types/{type_id}
PATCH  /lab-results/config/sample-types/{type_id}
DELETE /lab-results/config/sample-types/{type_id}

POST   /lab-results/config/sample-types/{type_id}/subtypes
DELETE /lab-results/config/sample-types/{type_id}/subtypes/{subtype_id}

POST   /lab-results/config/sample-types/{type_id}/unit-types
DELETE /lab-results/config/sample-types/{type_id}/unit-types/{unit_type_id}

POST   /lab-results/config/sample-types/{type_id}/turnaround-options
DELETE /lab-results/config/sample-types/{type_id}/turnaround-options/{option_id}

POST   /lab-results/config/sample-types/{type_id}/required-roles
DELETE /lab-results/config/sample-types/{type_id}/required-roles/{required_role_id}

POST   /lab-results/config/sample-types/{type_id}/wa-codes
DELETE /lab-results/config/sample-types/{type_id}/wa-codes/{wa_code_id}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import EmployeeRoleType, WACodeLevel
from app.lab_results.models import SampleType
from app.wa_codes.models import WACode

BASE = "/lab-results/config/sample-types"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_sample_type(
    db: AsyncSession,
    name: str = "Asbestos Air",
    allows_multiple_inspectors: bool = True,
) -> SampleType:
    st = SampleType(name=name, allows_multiple_inspectors=allows_multiple_inspectors)
    db.add(st)
    await db.flush()
    return st


async def _seed_wa_code(db: AsyncSession, code: str = "ACM-001") -> WACode:
    wc = WACode(
        code=code,
        description=f"WA code {code}",
        level=WACodeLevel.PROJECT,
    )
    db.add(wc)
    await db.flush()
    return wc


# ---------------------------------------------------------------------------
# Sample type CRUD
# ---------------------------------------------------------------------------


class TestListSampleTypes:
    async def test_returns_200(self, auth_client: AsyncClient, db_session: AsyncSession):
        await _seed_sample_type(db_session, "Bulk ACM")
        response = await auth_client.get(BASE)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_includes_created_type(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_sample_type(db_session, "Mold Air")
        response = await auth_client.get(BASE)
        names = [t["name"] for t in response.json()]
        assert "Mold Air" in names


class TestCreateSampleType:
    async def test_returns_201(self, auth_client: AsyncClient):
        response = await auth_client.post(BASE, json={"name": "Lead Wipe"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Lead Wipe"
        assert data["allows_multiple_inspectors"] is True
        assert data["subtypes"] == []
        assert data["unit_types"] == []

    async def test_duplicate_name_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_sample_type(db_session, "Duplicate Type")
        response = await auth_client.post(BASE, json={"name": "Duplicate Type"})
        assert response.status_code == 409

    async def test_single_inspector_flag(self, auth_client: AsyncClient):
        response = await auth_client.post(
            BASE,
            json={"name": "Single Inspector Type", "allows_multiple_inspectors": False},
        )
        assert response.status_code == 201
        assert response.json()["allows_multiple_inspectors"] is False


class TestGetSampleType:
    async def test_returns_200(self, auth_client: AsyncClient, db_session: AsyncSession):
        st = await _seed_sample_type(db_session, "Get Test Type")
        response = await auth_client.get(f"{BASE}/{st.id}")
        assert response.status_code == 200
        assert response.json()["id"] == st.id

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get(f"{BASE}/9999")
        assert response.status_code == 404


class TestUpdateSampleType:
    async def test_patch_name(self, auth_client: AsyncClient, db_session: AsyncSession):
        st = await _seed_sample_type(db_session, "Old Name")
        response = await auth_client.patch(f"{BASE}/{st.id}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_patch_allows_multiple_inspectors(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Multi Inspector Type", allows_multiple_inspectors=True)
        response = await auth_client.patch(
            f"{BASE}/{st.id}", json={"allows_multiple_inspectors": False}
        )
        assert response.status_code == 200
        assert response.json()["allows_multiple_inspectors"] is False

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.patch(f"{BASE}/9999", json={"name": "x"})
        assert response.status_code == 404


class TestDeleteSampleType:
    async def test_returns_204(self, auth_client: AsyncClient, db_session: AsyncSession):
        st = await _seed_sample_type(db_session, "To Delete Type")
        response = await auth_client.delete(f"{BASE}/{st.id}")
        assert response.status_code == 204

        follow_up = await auth_client.get(f"{BASE}/{st.id}")
        assert follow_up.status_code == 404

    async def test_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.delete(f"{BASE}/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Subtypes
# ---------------------------------------------------------------------------


class TestSubtypes:
    async def test_add_subtype_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Subtype Parent")
        response = await auth_client.post(
            f"{BASE}/{st.id}/subtypes", json={"name": "Friable"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Friable"
        assert data["sample_type_id"] == st.id

    async def test_subtype_appears_on_parent(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Subtype List Parent")
        await auth_client.post(f"{BASE}/{st.id}/subtypes", json={"name": "Non-Friable"})
        response = await auth_client.get(f"{BASE}/{st.id}")
        subtypes = response.json()["subtypes"]
        assert any(s["name"] == "Non-Friable" for s in subtypes)

    async def test_add_subtype_missing_type_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{BASE}/9999/subtypes", json={"name": "Ghost"}
        )
        assert response.status_code == 404

    async def test_delete_subtype_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Subtype Delete Parent")
        add = await auth_client.post(
            f"{BASE}/{st.id}/subtypes", json={"name": "To Remove"}
        )
        subtype_id = add.json()["id"]

        response = await auth_client.delete(f"{BASE}/{st.id}/subtypes/{subtype_id}")
        assert response.status_code == 204

    async def test_delete_subtype_wrong_parent_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st1 = await _seed_sample_type(db_session, "Parent A Subtypes")
        st2 = await _seed_sample_type(db_session, "Parent B Subtypes")
        add = await auth_client.post(
            f"{BASE}/{st1.id}/subtypes", json={"name": "Belongs to A"}
        )
        subtype_id = add.json()["id"]

        response = await auth_client.delete(f"{BASE}/{st2.id}/subtypes/{subtype_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Unit types
# ---------------------------------------------------------------------------


class TestUnitTypes:
    async def test_add_unit_type_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Unit Type Parent")
        response = await auth_client.post(
            f"{BASE}/{st.id}/unit-types", json={"name": "PCM Sample"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PCM Sample"
        assert data["sample_type_id"] == st.id

    async def test_unit_type_appears_on_parent(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Unit Type List Parent")
        await auth_client.post(f"{BASE}/{st.id}/unit-types", json={"name": "TEM Sample"})
        response = await auth_client.get(f"{BASE}/{st.id}")
        unit_types = response.json()["unit_types"]
        assert any(u["name"] == "TEM Sample" for u in unit_types)

    async def test_add_unit_type_missing_type_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{BASE}/9999/unit-types", json={"name": "Ghost"}
        )
        assert response.status_code == 404

    async def test_delete_unit_type_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Unit Type Delete Parent")
        add = await auth_client.post(
            f"{BASE}/{st.id}/unit-types", json={"name": "To Remove"}
        )
        unit_type_id = add.json()["id"]

        response = await auth_client.delete(f"{BASE}/{st.id}/unit-types/{unit_type_id}")
        assert response.status_code == 204

    async def test_delete_unit_type_wrong_parent_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st1 = await _seed_sample_type(db_session, "Parent A Unit Types")
        st2 = await _seed_sample_type(db_session, "Parent B Unit Types")
        add = await auth_client.post(
            f"{BASE}/{st1.id}/unit-types", json={"name": "Belongs to A"}
        )
        unit_type_id = add.json()["id"]

        response = await auth_client.delete(f"{BASE}/{st2.id}/unit-types/{unit_type_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Turnaround options
# ---------------------------------------------------------------------------


class TestTurnaroundOptions:
    async def test_add_turnaround_option_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "TAT Parent")
        response = await auth_client.post(
            f"{BASE}/{st.id}/turnaround-options",
            json={"hours": 24, "label": "Standard"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["hours"] == 24
        assert data["label"] == "Standard"
        assert data["sample_type_id"] == st.id

    async def test_turnaround_appears_on_parent(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "TAT List Parent")
        await auth_client.post(
            f"{BASE}/{st.id}/turnaround-options",
            json={"hours": 4, "label": "Rush"},
        )
        response = await auth_client.get(f"{BASE}/{st.id}")
        tat = response.json()["turnaround_options"]
        assert any(t["label"] == "Rush" for t in tat)

    async def test_add_tat_missing_type_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{BASE}/9999/turnaround-options",
            json={"hours": 24, "label": "Standard"},
        )
        assert response.status_code == 404

    async def test_delete_turnaround_option_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "TAT Delete Parent")
        add = await auth_client.post(
            f"{BASE}/{st.id}/turnaround-options",
            json={"hours": 48, "label": "Economy"},
        )
        option_id = add.json()["id"]

        response = await auth_client.delete(
            f"{BASE}/{st.id}/turnaround-options/{option_id}"
        )
        assert response.status_code == 204

    async def test_delete_tat_wrong_parent_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st1 = await _seed_sample_type(db_session, "Parent A TAT")
        st2 = await _seed_sample_type(db_session, "Parent B TAT")
        add = await auth_client.post(
            f"{BASE}/{st1.id}/turnaround-options",
            json={"hours": 24, "label": "Standard"},
        )
        option_id = add.json()["id"]

        response = await auth_client.delete(
            f"{BASE}/{st2.id}/turnaround-options/{option_id}"
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Required roles
# ---------------------------------------------------------------------------


class TestRequiredRoles:
    async def test_add_required_role_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Role Parent")
        response = await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role_type"] == EmployeeRoleType.ACM_AIR_TECH
        assert data["sample_type_id"] == st.id

    async def test_role_appears_on_parent(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Role List Parent")
        await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_INSPECTOR_A},
        )
        response = await auth_client.get(f"{BASE}/{st.id}")
        roles = response.json()["required_roles"]
        assert any(r["role_type"] == EmployeeRoleType.ACM_INSPECTOR_A for r in roles)

    async def test_duplicate_role_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Role Dupe Parent")
        await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        response = await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        assert response.status_code == 409

    async def test_different_roles_same_type_ok(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Role Multi Parent")
        r1 = await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        r2 = await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_INSPECTOR_A},
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

    async def test_add_role_missing_type_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.post(
            f"{BASE}/9999/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        assert response.status_code == 404

    async def test_delete_required_role_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "Role Delete Parent")
        add = await auth_client.post(
            f"{BASE}/{st.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_PROJECT_MONITOR},
        )
        required_role_id = add.json()["id"]

        response = await auth_client.delete(
            f"{BASE}/{st.id}/required-roles/{required_role_id}"
        )
        assert response.status_code == 204

    async def test_delete_role_wrong_parent_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st1 = await _seed_sample_type(db_session, "Parent A Roles")
        st2 = await _seed_sample_type(db_session, "Parent B Roles")
        add = await auth_client.post(
            f"{BASE}/{st1.id}/required-roles",
            json={"role_type": EmployeeRoleType.ACM_AIR_TECH},
        )
        required_role_id = add.json()["id"]

        response = await auth_client.delete(
            f"{BASE}/{st2.id}/required-roles/{required_role_id}"
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# WA codes
# ---------------------------------------------------------------------------


class TestWACodes:
    async def test_add_wa_code_returns_201(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code Parent")
        wc = await _seed_wa_code(db_session, "ACM-WA-001")
        response = await auth_client.post(
            f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": wc.id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["wa_code_id"] == wc.id
        assert data["sample_type_id"] == st.id

    async def test_wa_code_appears_on_parent(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code List Parent")
        wc = await _seed_wa_code(db_session, "ACM-WA-002")
        await auth_client.post(f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": wc.id})
        response = await auth_client.get(f"{BASE}/{st.id}")
        wa_codes = response.json()["wa_codes"]
        assert any(w["wa_code_id"] == wc.id for w in wa_codes)

    async def test_duplicate_wa_code_returns_409(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code Dupe Parent")
        wc = await _seed_wa_code(db_session, "ACM-WA-003")
        await auth_client.post(f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": wc.id})
        response = await auth_client.post(
            f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": wc.id}
        )
        assert response.status_code == 409

    async def test_missing_wa_code_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code 404 Parent")
        response = await auth_client.post(
            f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": 9999}
        )
        assert response.status_code == 404

    async def test_add_wa_code_missing_type_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        wc = await _seed_wa_code(db_session, "ACM-WA-005")
        response = await auth_client.post(
            f"{BASE}/9999/wa-codes", json={"wa_code_id": wc.id}
        )
        assert response.status_code == 404

    async def test_delete_wa_code_returns_204(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code Delete Parent")
        wc = await _seed_wa_code(db_session, "ACM-WA-006")
        await auth_client.post(f"{BASE}/{st.id}/wa-codes", json={"wa_code_id": wc.id})

        response = await auth_client.delete(f"{BASE}/{st.id}/wa-codes/{wc.id}")
        assert response.status_code == 204

    async def test_delete_wa_code_not_linked_returns_404(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        st = await _seed_sample_type(db_session, "WA Code Unlinked Parent")
        wc = await _seed_wa_code(db_session, "ACM-WA-007")
        response = await auth_client.delete(f"{BASE}/{st.id}/wa-codes/{wc.id}")
        assert response.status_code == 404
