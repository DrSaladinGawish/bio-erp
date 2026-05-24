"""P4 smoke tests — Bioreactor, CellLine, GeneConstruct, RawMaterial CRUD.

Run: pytest tests/test_p4_bio_entities.py -v
"""

from __future__ import annotations
from uuid import uuid4

import pytest
from httpx import AsyncClient

PREFIX = "/api/v1/manufacturing"

ENTITIES = {
    "bioreactors": {
        "create": lambda: {"reactor_code": f"BR-{uuid4().hex[:8].upper()}", "name": "Test Bioreactor", "working_volume_l": 500},
        "update": {"name": "Updated Bioreactor"},
    },
    "cell-lines": {
        "create": lambda: {"cell_code": f"CL-{uuid4().hex[:8].upper()}", "name": "CHO-K1", "cell_type": "CHO"},
        "update": {"name": "HEK293"},
    },
    "gene-constructs": {
        "create": lambda: {"construct_code": f"GC-{uuid4().hex[:8].upper()}", "name": "pCAG-GFP", "plasmid_size_kb": 5.5},
        "update": {"name": "pCAG-GFPv2"},
    },
    "raw-materials": {
        "create": lambda: {"material_code": f"RM-{uuid4().hex[:8].upper()}", "name": "Glucose", "unit_cost_egp": 10.0},
        "update": {"name": "D-Glucose"},
    },
}


class TestBioreactorCRUD:
    RESOURCE = "bioreactors"

    async def _create(self, client, auth_headers):
        return await client.post(f"{PREFIX}/{self.RESOURCE}", json=ENTITIES[self.RESOURCE]["create"](), headers=auth_headers)

    async def test_create_returns_201(self, client, auth_headers):
        r = await self._create(client, auth_headers)
        assert r.status_code == 201
        assert "id" in r.json()

    async def test_list_returns_200(self, client, auth_headers):
        r = await client.get(f"{PREFIX}/{self.RESOURCE}", headers=auth_headers)
        assert r.status_code == 200
        assert "data" in r.json()

    async def test_update_returns_200(self, client, auth_headers):
        created = await self._create(client, auth_headers)
        eid = created.json()["id"]
        r = await client.put(f"{PREFIX}/{self.RESOURCE}/{eid}", json=ENTITIES[self.RESOURCE]["update"], headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["name"] == ENTITIES[self.RESOURCE]["update"]["name"]

    async def test_delete_returns_200(self, client, auth_headers):
        created = await self._create(client, auth_headers)
        eid = created.json()["id"]
        r = await client.delete(f"{PREFIX}/{self.RESOURCE}/{eid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is True

    async def test_no_auth_returns_401(self, client):
        r = await client.get(f"{PREFIX}/{self.RESOURCE}")
        assert r.status_code == 401

    async def test_nonexistent_returns_404(self, client, auth_headers):
        r = await client.get(f"{PREFIX}/{self.RESOURCE}/99999", headers=auth_headers)
        assert r.status_code == 404


@pytest.mark.parametrize("resource", ["cell-lines", "gene-constructs", "raw-materials"])
class TestEntityCRUD:

    async def test_create_returns_201(self, resource, client, auth_headers):
        r = await client.post(f"{PREFIX}/{resource}", json=ENTITIES[resource]["create"](), headers=auth_headers)
        assert r.status_code == 201
        assert "id" in r.json()

    async def test_list_returns_200(self, resource, client, auth_headers):
        r = await client.get(f"{PREFIX}/{resource}", headers=auth_headers)
        assert r.status_code == 200

    async def test_update_returns_200(self, resource, client, auth_headers):
        created = await client.post(f"{PREFIX}/{resource}", json=ENTITIES[resource]["create"](), headers=auth_headers)
        eid = created.json()["id"]
        r = await client.put(f"{PREFIX}/{resource}/{eid}", json=ENTITIES[resource]["update"], headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["name"] == ENTITIES[resource]["update"]["name"]

    async def test_delete_returns_200(self, resource, client, auth_headers):
        created = await client.post(f"{PREFIX}/{resource}", json=ENTITIES[resource]["create"](), headers=auth_headers)
        eid = created.json()["id"]
        r = await client.delete(f"{PREFIX}/{resource}/{eid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is True

    async def test_no_auth_returns_401(self, resource, client):
        r = await client.get(f"{PREFIX}/{resource}")
        assert r.status_code == 401

    async def test_nonexistent_returns_404(self, resource, client, auth_headers):
        r = await client.get(f"{PREFIX}/{resource}/99999", headers=auth_headers)
        assert r.status_code == 404
