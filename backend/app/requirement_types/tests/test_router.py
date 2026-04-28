"""
Integration tests for GET /requirement-types.
"""

import pytest
from httpx import AsyncClient

from app.common.enums import DocumentType, RequirementEvent


class TestListRequirementTypes:
    async def test_401_without_auth(self, client: AsyncClient):
        response = await client.get("/requirement-types")
        assert response.status_code == 401

    async def test_returns_all_six_handlers(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-types")
        assert response.status_code == 200
        names = {item["name"] for item in response.json()}
        assert names == {
            "project_document",
            "contractor_payment_record",
            "lab_report",
            "project_dep_filing",
            "deliverable",
            "building_deliverable",
        }

    async def test_project_document_has_template_params_schema(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        schema = items["project_document"]["template_params_schema"]
        assert schema, "expected non-empty schema for project_document"
        # Pydantic emits DocumentType as a $def; verify the enum values are present
        defs = schema.get("$defs", {})
        assert "DocumentType" in defs
        schema_enum = set(defs["DocumentType"].get("enum", []))
        valid_values = {e.value for e in DocumentType}
        assert schema_enum == valid_values

    @pytest.mark.parametrize(
        "name",
        ["contractor_payment_record", "lab_report", "project_dep_filing", "deliverable", "building_deliverable"],
    )
    async def test_no_template_params_schema_for_other_types(
        self, auth_client: AsyncClient, name: str
    ):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert items[name]["template_params_schema"] == {}

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("project_document", True),
            ("contractor_payment_record", True),
            ("lab_report", True),
            ("project_dep_filing", True),
            ("deliverable", False),
            ("building_deliverable", False),
        ],
    )
    async def test_is_dismissable(self, auth_client: AsyncClient, name: str, expected: bool):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert items[name]["is_dismissable"] == expected

    async def test_project_document_events(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert set(items["project_document"]["events"]) == {
            RequirementEvent.TIME_ENTRY_CREATED,
            RequirementEvent.WA_CODE_ADDED,
            RequirementEvent.WA_CODE_REMOVED,
        }

    async def test_contractor_payment_record_events(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert set(items["contractor_payment_record"]["events"]) == {
            RequirementEvent.CONTRACTOR_LINKED,
            RequirementEvent.CONTRACTOR_UNLINKED,
        }

    async def test_lab_report_events(self, auth_client: AsyncClient):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert items["lab_report"]["events"] == [RequirementEvent.BATCH_CREATED]

    @pytest.mark.parametrize("name", ["project_dep_filing", "deliverable", "building_deliverable"])
    async def test_no_events(self, auth_client: AsyncClient, name: str):
        response = await auth_client.get("/requirement-types")
        items = {item["name"]: item for item in response.json()}
        assert items[name]["events"] == []
