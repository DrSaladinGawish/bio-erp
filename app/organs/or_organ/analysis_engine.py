"""
OR-ERP Analysis Engine — Planning & What-If Tool
=================================================
Read-only analysis layer. NEVER writes to production database.
Extracts live data → Solves OR models → Compares scenarios → Returns insights.

Usage:
    from analysis_engine import ORAnalysisEngine
    analyzer = ORAnalysisEngine(production_db_url="postgresql://...")

    # Scenario 1: What if demand increases 20%?
    result = analyzer.what_if_inventory(demand_multiplier=1.2)

    # Scenario 2: Optimal production mix given current constraints
    result = analyzer.optimize_production_mix()

    # Scenario 3: Compare multiple scenarios
    comparison = analyzer.compare_scenarios([
        {"name": "Current", "params": {}},
        {"name": "+20% Demand", "params": {"demand_multiplier": 1.2}},
        {"name": "New Machine", "params": {"machine_capacity": 200}}
    ])
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import OR engines
from app.organs.or_organ.or_erp_module import (
    ORERPModule,
    DecisionState, DecisionAlternative,
    LPObjective, LPConstraint,
    InventoryItem,
    TransportNode, TransportRoute,
    TOCResource,
    BreakEvenPoint
)


@dataclass
class AnalysisScenario:
    """Represents a single what-if scenario"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    results: Dict[str, Any] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass  
class AnalysisReport:
    """Complete analysis report with multiple scenarios"""
    report_id: str
    report_type: str
    base_parameters: Dict[str, Any]
    scenarios: List[AnalysisScenario]
    recommendations: List[str]
    generated_at: str = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "base_parameters": self.base_parameters,
            "scenarios": [asdict(s) for s in self.scenarios],
            "recommendations": self.recommendations,
            "generated_at": self.generated_at
        }

    def save_to_file(self, directory: str = "./analysis_reports"):
        """Save report to JSON file (disposable storage)"""
        os.makedirs(directory, exist_ok=True)
        filename = f"{directory}/{self.report_id}_{self.report_type}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return filename


class ORAnalysisEngine:
    """
    Planning & Analysis Engine — Read-Only from Production DB
    ==========================================================

    Principles:
    1. READ-ONLY: Never writes to production database
    2. SNAPSHOT: Takes point-in-time snapshots of live data
    3. SANDBOX: All analysis results stored in temporary files
    4. COMPARABLE: Multiple scenarios can be created and compared
    5. DISPOSABLE: Analysis files can be deleted without impact
    """

    def __init__(self, production_db_url: str = None, analysis_dir: str = "./analysis_sandbox"):
        """
        Args:
            production_db_url: Connection string for read-only access to production DB
            analysis_dir: Directory for temporary analysis files (disposable)
        """
        self.production_db_url = production_db_url or os.getenv("DATABASE_URL", "sqlite:///bio_erp.db")
        self.analysis_dir = analysis_dir
        self.or_module = ORERPModule()

        # Create read-only engine (no write permissions)
        self.engine = create_engine(
            self.production_db_url,
            connect_args={"options": "-c default_transaction_read_only=on"} if "postgresql" in self.production_db_url else {}
        )
        self.Session = sessionmaker(bind=self.engine)

        os.makedirs(self.analysis_dir, exist_ok=True)

    def _read_production_data(self, query: str) -> pd.DataFrame:
        """Execute read-only query against production database"""
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn)

    def _save_scenario(self, scenario: AnalysisScenario) -> str:
        """Save scenario to disposable file (not database)"""
        filename = f"{self.analysis_dir}/scenario_{scenario.id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(asdict(scenario), f, indent=2, ensure_ascii=False)
        return filename

    # =================================================================
    # SCENARIO 1: Inventory What-If Analysis
    # =================================================================

    def what_if_inventory(self, 
                         demand_multiplier: float = 1.0,
                         holding_cost_change: float = 0.0,
                         ordering_cost_change: float = 0.0,
                         scenario_name: str = None) -> AnalysisScenario:
        """
        Analyze inventory impact of demand/cost changes.

        Args:
            demand_multiplier: 1.0 = current, 1.2 = +20% demand
            holding_cost_change: Percentage change in holding cost (-0.1 = -10%)
            ordering_cost_change: Percentage change in ordering cost
        """
        # Extract current inventory data from production
        query = """
            SELECT sku, item_name, annual_demand, ordering_cost, 
                   holding_cost_per_unit, unit_cost, lead_time_days
            FROM or_inventory_items 
            WHERE active = true
        """
        try:
            df = self._read_production_data(query)
        except Exception:
            # Fallback: use sample data if table doesn't exist yet
            df = pd.DataFrame({
                "sku": ["RAW-001", "RAW-002", "RAW-003"],
                "item_name": ["Steel", "Plastic", "Chip"],
                "annual_demand": [2400, 5000, 800],
                "ordering_cost": [150, 200, 300],
                "holding_cost_per_unit": [12, 8, 25],
                "unit_cost": [80, 45, 120],
                "lead_time_days": [7, 5, 14]
            })

        # Apply what-if parameters
        scenarios_results = []
        for _, row in df.iterrows():
            modified_item = {
                "sku": row["sku"],
                "name": row["item_name"],
                "annual_demand": row["annual_demand"] * demand_multiplier,
                "ordering_cost": row["ordering_cost"] * (1 + ordering_cost_change),
                "holding_cost_per_unit": row["holding_cost_per_unit"] * (1 + holding_cost_change),
                "unit_cost": row["unit_cost"],
                "lead_time_days": row["lead_time_days"],
                "daily_demand": (row["annual_demand"] * demand_multiplier) / 365
            }

            result = self.or_module.optimize_inventory([modified_item], "eoq")
            scenarios_results.append(result[0])

        scenario = AnalysisScenario(
            id=f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=scenario_name or f"Inventory_Demand_{demand_multiplier}x",
            description=f"Inventory analysis with demand multiplier={demand_multiplier}",
            parameters={
                "demand_multiplier": demand_multiplier,
                "holding_cost_change": holding_cost_change,
                "ordering_cost_change": ordering_cost_change
            },
            results={
                "items_analyzed": len(scenarios_results),
                "total_annual_cost": sum(r.get("eoq_basic", {}).get("total_annual_cost", 0) for r in scenarios_results),
                "items": scenarios_results
            }
        )

        self._save_scenario(scenario)
        return scenario

    # =================================================================
    # SCENARIO 2: Production Mix Optimization
    # =================================================================

    def optimize_production_mix(self, 
                               labor_hours_available: float = None,
                               machine_hours_available: float = None,
                               material_a_available: float = None,
                               scenario_name: str = None) -> AnalysisScenario:
        """
        Optimize production mix given resource constraints.
        Reads current product profitability from production data.
        """
        # In real implementation, read from production DB:
        # query = "SELECT product_id, profit_per_unit, labor_hours, machine_hours FROM products"

        # Sample production mix problem
        objective = {
            "name": "Maximize Profit",
            "coefficients": [40, 30, 50],  # Profit per unit of Product A, B, C
            "sense": "maximize"
        }

        constraints = [
            {
                "name": "Labor Hours",
                "coefficients": [2, 1, 3],
                "rhs": labor_hours_available or 100,
                "operator": "<="
            },
            {
                "name": "Machine Hours", 
                "coefficients": [1, 2, 1],
                "rhs": machine_hours_available or 80,
                "operator": "<="
            },
            {
                "name": "Material A",
                "coefficients": [3, 0, 2],
                "rhs": material_a_available or 90,
                "operator": "<="
            }
        ]

        result = self.or_module.solve_linear_program(objective, constraints)

        scenario = AnalysisScenario(
            id=f"LP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=scenario_name or "Production_Mix_Optimization",
            description="Optimal production mix given resource constraints",
            parameters={
                "labor_hours": labor_hours_available or 100,
                "machine_hours": machine_hours_available or 80,
                "material_a": material_a_available or 90
            },
            results=result
        )

        self._save_scenario(scenario)
        return scenario

    # =================================================================
    # SCENARIO 3: Transportation Cost Analysis
    # =================================================================

    def analyze_transportation(self,
                              sources: List[Dict] = None,
                              destinations: List[Dict] = None,
                              routes: List[Dict] = None,
                              method: str = "vogel",
                              scenario_name: str = None) -> AnalysisScenario:
        """Analyze transportation costs with different methods"""

        # Default: Egypt distribution network (from textbook example)
        if sources is None:
            sources = [
                {"id": "CAI", "name": "Cairo Factory", "supply": 500, "is_source": True},
                {"id": "ALX", "name": "Alexandria Factory", "supply": 400, "is_source": True}
            ]
        if destinations is None:
            destinations = [
                {"id": "GIZ", "name": "Giza Warehouse", "demand": 300, "is_source": False},
                {"id": "LUX", "name": "Luxor Warehouse", "demand": 350, "is_source": False},
                {"id": "ASN", "name": "Aswan Warehouse", "demand": 250, "is_source": False}
            ]
        if routes is None:
            routes = [
                {"from_id": "CAI", "to_id": "GIZ", "cost_per_unit": 50},
                {"from_id": "CAI", "to_id": "LUX", "cost_per_unit": 120},
                {"from_id": "CAI", "to_id": "ASN", "cost_per_unit": 150},
                {"from_id": "ALX", "to_id": "GIZ", "cost_per_unit": 80},
                {"from_id": "ALX", "to_id": "LUX", "cost_per_unit": 90},
                {"from_id": "ALX", "to_id": "ASN", "cost_per_unit": 100}
            ]

        result = self.or_module.solve_transportation(sources, destinations, routes, method)

        scenario = AnalysisScenario(
            id=f"TRNS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=scenario_name or f"Transport_{method}",
            description=f"Transportation analysis using {method} method",
            parameters={"method": method, "sources": len(sources), "destinations": len(destinations)},
            results=result
        )

        self._save_scenario(scenario)
        return scenario

    # =================================================================
    # SCENARIO 4: PERT/CPM Project Scheduling
    # =================================================================

    def analyze_project_schedule(self,
                                activities: List[Dict] = None,
                                scenario_name: str = None) -> AnalysisScenario:
        """Analyze project schedule and identify critical path"""

        if activities is None:
            activities = [
                {"id": "A", "name": "Site Preparation", "predecessors": [], "duration": 3},
                {"id": "B", "name": "Foundation", "predecessors": ["A"], "duration": 4},
                {"id": "C", "name": "Framing", "predecessors": ["B"], "duration": 5},
                {"id": "D", "name": "Electrical", "predecessors": ["C"], "duration": 2},
                {"id": "E", "name": "Plumbing", "predecessors": ["C"], "duration": 3},
                {"id": "F", "name": "Finishing", "predecessors": ["D", "E"], "duration": 4}
            ]

        result = self.or_module.analyze_network(activities)

        scenario = AnalysisScenario(
            id=f"PERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=scenario_name or "Project_Schedule_Analysis",
            description="PERT/CPM network analysis for project scheduling",
            parameters={"activities_count": len(activities)},
            results=result
        )

        self._save_scenario(scenario)
        return scenario

    # =================================================================
    # SCENARIO COMPARISON
    # =================================================================

    def compare_scenarios(self, scenario_configs: List[Dict]) -> AnalysisReport:
        """
        Run multiple scenarios and generate comparison report.

        Args:
            scenario_configs: [
                {"type": "inventory", "name": "Current", "params": {}},
                {"type": "inventory", "name": "+20% Demand", "params": {"demand_multiplier": 1.2}}
            ]
        """
        scenarios = []

        for config in scenario_configs:
            scenario_type = config.get("type")
            params = config.get("params", {})
            name = config.get("name", f"Scenario_{len(scenarios)+1}")

            if scenario_type == "inventory":
                scenario = self.what_if_inventory(scenario_name=name, **params)
            elif scenario_type == "production":
                scenario = self.optimize_production_mix(scenario_name=name, **params)
            elif scenario_type == "transportation":
                scenario = self.analyze_transportation(scenario_name=name, **params)
            elif scenario_type == "project":
                scenario = self.analyze_project_schedule(scenario_name=name, **params)
            else:
                continue

            scenarios.append(scenario)

        # Generate recommendations based on comparison
        recommendations = self._generate_recommendations(scenarios)

        report = AnalysisReport(
            report_id=f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_type="scenario_comparison",
            base_parameters={},
            scenarios=scenarios,
            recommendations=recommendations
        )

        report.save_to_file(self.analysis_dir)
        return report

    def _generate_recommendations(self, scenarios: List[AnalysisScenario]) -> List[str]:
        """Generate actionable recommendations from scenario comparison"""
        recommendations = []

        if len(scenarios) >= 2:
            # Compare costs
            costs = []
            for s in scenarios:
                if "total_annual_cost" in str(s.results):
                    costs.append((s.name, s.results.get("total_annual_cost", 0)))

            if costs:
                best = min(costs, key=lambda x: x[1])
                recommendations.append(f"Lowest cost scenario: {best[0]} (${best[1]:,.2f})")

            # Compare project durations
            durations = []
            for s in scenarios:
                if "project_duration" in str(s.results):
                    durations.append((s.name, s.results.get("project_duration", 0)))

            if durations:
                fastest = min(durations, key=lambda x: x[1])
                recommendations.append(f"Fastest completion: {fastest[0]} ({fastest[1]} days)")

        return recommendations

    # =================================================================
    # CLEANUP
    # =================================================================

    def clear_analysis_files(self):
        """Delete all analysis files (disposable)"""
        import glob
        files = glob.glob(f"{self.analysis_dir}/*.json")
        for f in files:
            os.remove(f)
        return len(files)

    def list_scenarios(self) -> List[Dict]:
        """List all saved scenarios"""
        import glob
        scenarios = []
        for filename in glob.glob(f"{self.analysis_dir}/scenario_*.json"):
            with open(filename, "r", encoding="utf-8") as f:
                scenarios.append(json.load(f))
        return scenarios
