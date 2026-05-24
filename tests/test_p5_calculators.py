"""P5 tests — Bio-manufacturing calculators (18 tests: 3 per calculator).

Run: pytest tests/test_p5_calculators.py -v
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

BASE = "/api/v1/bio/calculators"


# ═══════════════════════════════════════════════════════════════════
#  1. ATP Cost
# ═══════════════════════════════════════════════════════════════════

class TestATPCalculator:

    async def test_valid(self, client: AsyncClient):
        r = await client.post(f"{BASE}/atp", json={"substrate_mol": 10, "atp_per_mol": 36})
        assert r.status_code == 200
        body = r.json()
        assert body["total_atp_mol"] == 360
        assert body["total_cost_egp"] == 0.36
        assert body["cost_per_product_mol"] == pytest.approx(0.036, rel=1e-6)

    async def test_negative_input_returns_400(self, client: AsyncClient):
        r = await client.post(f"{BASE}/atp", json={"substrate_mol": -1, "atp_per_mol": 36})
        assert r.status_code == 422

    async def test_zero_input(self, client: AsyncClient):
        r = await client.post(f"{BASE}/atp", json={"substrate_mol": 0, "atp_per_mol": 36})
        assert r.status_code == 200
        assert r.json()["total_atp_mol"] == 0


# ═══════════════════════════════════════════════════════════════════
#  2. Enzyme Efficiency
# ═══════════════════════════════════════════════════════════════════

class TestEnzymeCalculator:

    async def test_valid(self, client: AsyncClient):
        r = await client.post(f"{BASE}/enzyme", json={"vmax": 100, "km": 5, "substrate_conc": 10})
        assert r.status_code == 200
        assert r.json()["reaction_rate"] == 100 * 10 / (5 + 10)

    async def test_km_zero_returns_422(self, client: AsyncClient):
        r = await client.post(f"{BASE}/enzyme", json={"vmax": 100, "km": 0, "substrate_conc": 10})
        assert r.status_code == 422

    async def test_negative_substrate_returns_422(self, client: AsyncClient):
        r = await client.post(f"{BASE}/enzyme", json={"vmax": 100, "km": 5, "substrate_conc": -1})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  3. Batch Optimization
# ═══════════════════════════════════════════════════════════════════

class TestOptimizationCalculator:

    async def test_valid_feasible(self, client: AsyncClient):
        r = await client.post(f"{BASE}/optimize", json={
            "biomass_target_gl": 10, "time_limit_hr": 168, "cost_constraint_egp": 10000,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["feasible"] is True
        assert body["optimal_yield_gl"] == 10

    async def test_infeasible(self, client: AsyncClient):
        r = await client.post(f"{BASE}/optimize", json={
            "biomass_target_gl": 1e6, "time_limit_hr": 1, "cost_constraint_egp": 1e9,
        })
        assert r.status_code == 200
        assert r.json()["feasible"] is False

    async def test_negative_target_returns_422(self, client: AsyncClient):
        r = await client.post(f"{BASE}/optimize", json={
            "biomass_target_gl": -1, "time_limit_hr": 168, "cost_constraint_egp": 10000,
        })
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  4. Sensitivity Analysis
# ═══════════════════════════════════════════════════════════════════

class TestSensitivityCalculator:

    async def test_valid(self, client: AsyncClient):
        r = await client.post(f"{BASE}/sensitivity", json={"base_value": 7.0, "param_range": 2.0, "steps": 5})
        assert r.status_code == 200
        body = r.json()
        assert "results" in body
        assert len(body["results"]) == 5

    async def test_min_steps(self, client: AsyncClient):
        r = await client.post(f"{BASE}/sensitivity", json={"base_value": 5.0, "param_range": 1.0, "steps": 2})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    async def test_steps_below_2_returns_422(self, client: AsyncClient):
        r = await client.post(f"{BASE}/sensitivity", json={"base_value": 5.0, "param_range": 1.0, "steps": 1})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  5. Gene Expression Cost
# ═══════════════════════════════════════════════════════════════════

class TestGeneCostCalculator:

    async def test_valid_iptg(self, client: AsyncClient):
        r = await client.post(f"{BASE}/gene-cost", json={"plasmid_size_kb": 5, "copy_number": 50})
        assert r.status_code == 200
        body = r.json()
        assert body["construction_cost_egp"] > 0
        assert body["induction_cost_egp"] == 5.0

    async def test_valid_constitutive(self, client: AsyncClient):
        r = await client.post(f"{BASE}/gene-cost", json={
            "plasmid_size_kb": 5, "copy_number": 50, "induction_method": "constitutive",
        })
        assert r.status_code == 200
        assert r.json()["induction_cost_egp"] == 0.0

    async def test_negative_size_returns_422(self, client: AsyncClient):
        r = await client.post(f"{BASE}/gene-cost", json={"plasmid_size_kb": -1, "copy_number": 50})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  6. Organ Line Throughput
# ═══════════════════════════════════════════════════════════════════

class TestThroughputCalculator:

    async def test_valid_liver(self, client: AsyncClient):
        r = await client.post(f"{BASE}/throughput", json={"organ_type": "liver"})
        assert r.status_code == 200
        body = r.json()
        assert body["efficiency_factor"] == 0.8
        assert body["throughput_million_cells_per_day"] > 0

    async def test_valid_kidney(self, client: AsyncClient):
        r = await client.post(f"{BASE}/throughput", json={"organ_type": "kidney", "cell_density_cells_per_ml": 5e6})
        assert r.status_code == 200
        assert r.json()["efficiency_factor"] == 0.6

    async def test_unknown_organ_defaults_to_0_5(self, client: AsyncClient):
        r = await client.post(f"{BASE}/throughput", json={"organ_type": "brain"})
        assert r.status_code == 200
        assert r.json()["efficiency_factor"] == 0.5
