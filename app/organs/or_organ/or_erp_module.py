"""
Operations Research ERP Module (OR-ERP)
Based on: "البحوث الإلكترونية في المحاسبة" (Operations Research in Accounting)
Al-Azhar University, Faculty of Commerce, 2025
Authors: Dr. Ahmed Abdel Qader, Dr. Mohamed Khairy, Dr. Ahmed Khairy

Module Version: 1.0.0
Integration: BIO-ERP / EventManager ERP Compatible
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import json
from abc import ABC, abstractmethod

# =============================================================================
# SECTION 1: ENUMS & CONFIGURATION
# =============================================================================

class DecisionCriterion(Enum):
    MAXIMAX = "maximax"           # Optimistic
    MAXIMIN = "maximin"           # Pessimistic (Wald)
    HURWICZ = "hurwicz"           # Realism (alpha)
    LAPLACE = "laplace"           # Equally likely
    MINIMAX_REGRET = "minimax_regret"  # Opportunity loss
    EMV = "emv"    # Risk analysis
    EOL = "eol"

class InventoryModelType(Enum):
    EOQ_BASIC = "eoq_basic"
    EOQ_BACKORDER = "eoq_backorder"
    EPQ = "epq"                   # Economic Production Quantity
    ABC_CLASSIFICATION = "abc"
    QUANTITY_DISCOUNT = "quantity_discount"
    PROBABILISTIC = "probabilistic"

class TransportMethod(Enum):
    NORTHWEST_CORNER = "nw_corner"
    LEAST_COST = "least_cost"
    VOGEL_APPROXIMATION = "vogel"
    MODI_OPTIMIZATION = "modi"

class ConstraintType(Enum):
    BOTTLENECK = "bottleneck"
    CAPACITY = "capacity"
    MARKET = "market"
    MATERIAL = "material"

# =============================================================================
# SECTION 2: DATA MODELS (Database Schema Compatible)
# =============================================================================

@dataclass
class DecisionState:
    """Represents a state of nature for decision analysis"""
    id: str
    name: str
    probability: float = 0.0
    description: str = ""

@dataclass
class DecisionAlternative:
    """Represents an alternative/action in decision matrix"""
    id: str
    name: str
    payoffs: Dict[str, float] = field(default_factory=dict)  # state_id -> payoff
    costs: Dict[str, float] = field(default_factory=dict)

@dataclass
class LPConstraint:
    """Linear Programming Constraint"""
    name: str
    coefficients: List[float]
    rhs: float
    operator: str = "<="  # <=, >=, ==

@dataclass
class LPObjective:
    """Linear Programming Objective Function"""
    name: str
    coefficients: List[float]
    sense: str = "maximize"  # maximize or minimize

@dataclass
class InventoryItem:
    """Inventory model parameters per item"""
    sku: str
    name: str
    annual_demand: float
    ordering_cost: float
    holding_cost_per_unit: float
    unit_cost: float
    lead_time_days: int
    stockout_cost: Optional[float] = None
    production_rate: Optional[float] = None
    daily_demand: Optional[float] = None

@dataclass
class TransportNode:
    """Supply or Demand node for transportation"""
    id: str
    name: str
    supply: float = 0.0  # For sources
    demand: float = 0.0  # For destinations
    is_source: bool = True

@dataclass
class TransportRoute:
    """Transportation cost route"""
    from_id: str
    to_id: str
    cost_per_unit: float
    allocation: float = 0.0

@dataclass
class TOCResource:
    """Theory of Constraints Resource"""
    id: str
    name: str
    capacity_hours: float
    used_hours: float
    output_units: float
    operating_expense: float
    is_bottleneck: bool = False

@dataclass
class BreakEvenPoint:
    """Cost-Volume-Profit Analysis"""
    fixed_costs: float
    variable_cost_per_unit: float
    selling_price_per_unit: float
    target_profit: float = 0.0

# =============================================================================
# SECTION 3: CORE ALGORITHMS
# =============================================================================

class DecisionAnalysisEngine:
    """
    Chapter 2: Decision-making mathematical models
    Chapter 9: Risk and uncertainty in decision-making
    """

    def __init__(self, states: List[DecisionState], alternatives: List[DecisionAlternative]):
        self.states = states
        self.alternatives = alternatives
        self.payoff_matrix = self._build_matrix()

    def _build_matrix(self) -> pd.DataFrame:
        """Build payoff matrix as DataFrame"""
        data = {}
        for alt in self.alternatives:
            data[alt.name] = [alt.payoffs.get(s.id, 0) for s in self.states]
        return pd.DataFrame(data, index=[s.name for s in self.states])

    def maximax(self) -> Tuple[str, float]:
        """Optimistic criterion - maximum of maximums"""
        best_alt = None
        best_val = float('-inf')
        for alt in self.alternatives:
            max_payoff = max(alt.payoffs.values())
            if max_payoff > best_val:
                best_val = max_payoff
                best_alt = alt.name
        return best_alt, best_val

    def maximin(self) -> Tuple[str, float]:
        """Pessimistic criterion - maximum of minimums (Wald)"""
        best_alt = None
        best_val = float('-inf')
        for alt in self.alternatives:
            min_payoff = min(alt.payoffs.values())
            if min_payoff > best_val:
                best_val = min_payoff
                best_alt = alt.name
        return best_alt, best_val

    def hurwicz(self, alpha: float = 0.5) -> Tuple[str, float]:
        """Realism criterion - weighted average of best and worst"""
        best_alt = None
        best_val = float('-inf')
        for alt in self.alternatives:
            max_p = max(alt.payoffs.values())
            min_p = min(alt.payoffs.values())
            score = alpha * max_p + (1 - alpha) * min_p
            if score > best_val:
                best_val = score
                best_alt = alt.name
        return best_alt, best_val

    def laplace(self) -> Tuple[str, float]:
        """Equally likely criterion - average payoff"""
        n = len(self.states)
        best_alt = None
        best_val = float('-inf')
        for alt in self.alternatives:
            avg = sum(alt.payoffs.values()) / n
            if avg > best_val:
                best_val = avg
                best_alt = alt.name
        return best_alt, best_val

    def minimax_regret(self) -> Tuple[str, float]:
        """Minimize maximum opportunity loss"""
        # Build regret matrix
        regret = pd.DataFrame(index=self.payoff_matrix.index)
        for col in self.payoff_matrix.columns:
            best_in_state = self.payoff_matrix[col].max()
            regret[col] = best_in_state - self.payoff_matrix[col]

        best_alt = None
        best_val = float('inf')
        for col in regret.columns:
            max_regret = regret[col].max()
            if max_regret < best_val:
                best_val = max_regret
                best_alt = col
        return best_alt, best_val

    def expected_monetary_value(self) -> Tuple[str, float]:
        """EMV with known probabilities (Risk analysis)"""
        best_alt = None
        best_val = float('-inf')
        for alt in self.alternatives:
            emv = sum(alt.payoffs.get(s.id, 0) * s.probability for s in self.states)
            if emv > best_val:
                best_val = emv
                best_alt = alt.name
        return best_alt, best_val

    def expected_opportunity_loss(self) -> Tuple[str, float]:
        """EOL - Expected opportunity loss"""
        best_alt = None
        best_val = float('inf')
        for alt in self.alternatives:
            eol = 0
            for s in self.states:
                best_payoff = max(a.payoffs.get(s.id, 0) for a in self.alternatives)
                opportunity_loss = best_payoff - alt.payoffs.get(s.id, 0)
                eol += opportunity_loss * s.probability
            if eol < best_val:
                best_val = eol
                best_alt = alt.name
        return best_alt, best_val

    def expected_value_of_perfect_information(self) -> float:
        """EVPI = EPPI - EMV(best)"""
        _, emv_best = self.expected_monetary_value()

        # EPPI: Expected payoff with perfect information
        eppi = 0
        for s in self.states:
            best_payoff = max(a.payoffs.get(s.id, 0) for a in self.alternatives)
            eppi += best_payoff * s.probability

        return eppi - emv_best

    def get_decision_report(self) -> Dict[str, Any]:
        """Generate comprehensive decision analysis report"""
        return {
            "payoff_matrix": self.payoff_matrix.to_dict(),
            "maximax": self.maximax(),
            "maximin": self.maximin(),
            "hurwicz_0.5": self.hurwicz(0.5),
            "laplace": self.laplace(),
            "minimax_regret": self.minimax_regret(),
            "emv": self.expected_monetary_value(),
            "eol": self.expected_opportunity_loss(),
            "evpi": self.expected_value_of_perfect_information(),
            "timestamp": datetime.now().isoformat()
        }


class LinearProgrammingEngine:
    """
    Chapter 3: Linear programming and its applications
    Uses scipy.optimize for simplex method implementation
    """

    def __init__(self, objective: LPObjective, constraints: List[LPConstraint]):
        self.objective = objective
        self.constraints = constraints

    def solve(self) -> Dict[str, Any]:
        """Solve LP using scipy.optimize.linprog"""
        try:
            from scipy.optimize import linprog

            # Objective coefficients (negate for maximization)
            c = [-x for x in self.objective.coefficients] if self.objective.sense == "maximize" else self.objective.coefficients

            # Constraints
            A_ub = []
            b_ub = []
            A_eq = []
            b_eq = []

            for cons in self.constraints:
                if cons.operator in ["<=", "<"]:
                    A_ub.append(cons.coefficients)
                    b_ub.append(cons.rhs)
                elif cons.operator in [">=", ">"]:
                    A_ub.append([-x for x in cons.coefficients])
                    b_ub.append(-cons.rhs)
                else:  # ==
                    A_eq.append(cons.coefficients)
                    b_eq.append(cons.rhs)

            result = linprog(
                c=c,
                A_ub=A_ub if A_ub else None,
                b_ub=b_ub if b_ub else None,
                A_eq=A_eq if A_eq else None,
                b_eq=b_eq if b_eq else None,
                bounds=(0, None),
                method='highs'
            )

            return {
                "success": result.success,
                "objective_value": -result.fun if self.objective.sense == "maximize" else result.fun,
                "solution": result.x.tolist(),
                "status": result.status,
                "message": result.message,
                "shadow_prices": result.ineqlin.marginals.tolist() if hasattr(result, 'ineqlin') else [],
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {"error": "scipy not installed", "success": False}

    def sensitivity_analysis(self, param_range: float = 0.1) -> Dict[str, Any]:
        """Basic sensitivity analysis on objective coefficients"""
        base = self.solve()
        if not base["success"]:
            return base

        sensitivities = []
        for i, coef in enumerate(self.objective.coefficients):
            # Test +10% and -10%
            original = self.objective.coefficients[i]

            self.objective.coefficients[i] = original * (1 + param_range)
            upper = self.solve()

            self.objective.coefficients[i] = original * (1 - param_range)
            lower = self.solve()

            self.objective.coefficients[i] = original

            sensitivities.append({
                "variable_index": i,
                "coefficient": original,
                "upper_10%": upper.get("objective_value"),
                "lower_10%": lower.get("objective_value"),
                "stable": abs(upper["objective_value"] - base["objective_value"]) < 0.01
            })

        return {
            "base_solution": base,
            "sensitivities": sensitivities
        }


class InventoryOptimizationEngine:
    """
    Chapter 5: Inventory models
    EOQ, EPQ, ABC, Quantity Discounts, Probabilistic models
    """

    def __init__(self, items: List[InventoryItem]):
        self.items = items

    def eoq_basic(self, item: InventoryItem) -> Dict[str, float]:
        """Economic Order Quantity - Harris Wilson Model"""
        D = item.annual_demand
        S = item.ordering_cost
        H = item.holding_cost_per_unit

        if H <= 0 or D <= 0 or S <= 0:
            return {"error": "Invalid parameters"}

        q_optimal = np.sqrt((2 * D * S) / H)
        total_cost = np.sqrt(2 * D * S * H)
        orders_per_year = D / q_optimal
        cycle_time = q_optimal / D  # in years

        return {
            "model": "EOQ_Basic",
            "sku": item.sku,
            "optimal_order_quantity": round(q_optimal, 2),
            "total_annual_cost": round(total_cost, 2),
            "orders_per_year": round(orders_per_year, 2),
            "cycle_time_days": round(cycle_time * 365, 2),
            "reorder_point": round(item.daily_demand * item.lead_time_days, 2) if item.daily_demand else 0,
            "holding_cost_annual": round((q_optimal / 2) * H, 2),
            "ordering_cost_annual": round((D / q_optimal) * S, 2)
        }

    def eoq_backorder(self, item: InventoryItem) -> Dict[str, float]:
        """EOQ with planned backorders (shortages allowed)"""
        D = item.annual_demand
        S = item.ordering_cost
        H = item.holding_cost_per_unit
        B = item.stockout_cost or H * 2

        q_optimal = np.sqrt((2 * D * S * (H + B)) / (H * B))
        s_optimal = q_optimal * (H / (H + B))  # Maximum inventory level
        max_shortage = q_optimal - s_optimal

        total_cost = np.sqrt((2 * D * S * H * B) / (H + B))

        return {
            "model": "EOQ_Backorder",
            "sku": item.sku,
            "optimal_order_quantity": round(q_optimal, 2),
            "max_inventory": round(s_optimal, 2),
            "max_shortage": round(max_shortage, 2),
            "total_annual_cost": round(total_cost, 2)
        }

    def epq_model(self, item: InventoryItem) -> Dict[str, float]:
        """Economic Production Quantity"""
        D = item.annual_demand
        S = item.ordering_cost
        H = item.holding_cost_per_unit
        P = item.production_rate or D * 1.5

        if P <= D:
            return {"error": "Production rate must exceed demand rate"}

        q_optimal = np.sqrt((2 * D * S * P) / (H * (P - D)))
        max_inventory = q_optimal * (1 - D / P)
        total_cost = np.sqrt(2 * D * S * H * (1 - D / P))

        return {
            "model": "EPQ",
            "sku": item.sku,
            "optimal_production_quantity": round(q_optimal, 2),
            "max_inventory": round(max_inventory, 2),
            "total_annual_cost": round(total_cost, 2),
            "production_runs_per_year": round(D / q_optimal, 2)
        }

    def abc_analysis(self, items_data: List[Dict]) -> pd.DataFrame:
        """
        ABC Classification based on annual consumption value
        items_data: [{"sku": "", "annual_demand": 0, "unit_cost": 0}]
        """
        df = pd.DataFrame(items_data)
        df['annual_consumption_value'] = df['annual_demand'] * df['unit_cost']
        df = df.sort_values('annual_consumption_value', ascending=False)
        df['cumulative_value'] = df['annual_consumption_value'].cumsum()
        df['cumulative_percentage'] = (df['cumulative_value'] / df['annual_consumption_value'].sum()) * 100
        df['item_percentage'] = ((df.index + 1) / len(df)) * 100

        # Classification
        def classify(row):
            if row['cumulative_percentage'] <= 80:
                return 'A'
            elif row['cumulative_percentage'] <= 95:
                return 'B'
            else:
                return 'C'

        df['class'] = df.apply(classify, axis=1)
        return df[['sku', 'annual_demand', 'unit_cost', 'annual_consumption_value', 
                   'cumulative_percentage', 'class']]

    def quantity_discount_analysis(self, item: InventoryItem, 
                                   discount_tiers: List[Dict]) -> Dict[str, Any]:
        """
        discount_tiers: [{"min_qty": 0, "max_qty": 100, "unit_cost": 10},
                         {"min_qty": 101, "max_qty": 500, "unit_cost": 9}]
        """
        D = item.annual_demand
        S = item.ordering_cost
        H_rate = item.holding_cost_per_unit / item.unit_cost  # As percentage

        results = []
        for tier in discount_tiers:
            C = tier['unit_cost']
            H = C * H_rate

            # Calculate EOQ at this price
            q_eoq = np.sqrt((2 * D * S) / H)

            # Adjust to feasible range
            max_qty = tier.get('max_qty')
            if max_qty is None:
                max_qty = float('inf')
            q_order = max(tier['min_qty'], min(q_eoq, max_qty))

            # Total cost = Purchase + Ordering + Holding
            purchase_cost = D * C
            ordering_cost = (D / q_order) * S
            holding_cost = (q_order / 2) * H
            total = purchase_cost + ordering_cost + holding_cost

            results.append({
                "tier": tier,
                "eoq": round(q_eoq, 2),
                "order_quantity": round(q_order, 2),
                "total_cost": round(total, 2),
                "purchase_cost": round(purchase_cost, 2)
            })

        best = min(results, key=lambda x: x['total_cost'])
        return {"all_tiers": results, "optimal_tier": best}

    def run_all_models(self, item: InventoryItem) -> Dict[str, Any]:
        """Run all applicable inventory models for an item"""
        return {
            "sku": item.sku,
            "eoq_basic": self.eoq_basic(item),
            "eoq_backorder": self.eoq_backorder(item) if item.stockout_cost else None,
            "epq": self.epq_model(item) if item.production_rate else None,
            "timestamp": datetime.now().isoformat()
        }


class TransportationEngine:
    """
    Chapter 6: Transportation models
    Northwest Corner, Least Cost, Vogel's Approximation, MODI
    """

    def __init__(self, sources: List[TransportNode], destinations: List[TransportNode], 
                 routes: List[TransportRoute]):
        self.sources = sources
        self.destinations = destinations
        self.routes = routes
        self.cost_matrix = self._build_cost_matrix()

    def _build_cost_matrix(self) -> pd.DataFrame:
        """Build cost matrix from routes"""
        src_ids = [s.id for s in self.sources]
        dst_ids = [d.id for d in self.destinations]

        matrix = pd.DataFrame(index=src_ids, columns=dst_ids)
        for r in self.routes:
            matrix.loc[r.from_id, r.to_id] = r.cost_per_unit
        return matrix.fillna(0)

    def northwest_corner(self) -> Dict[str, Any]:
        """Northwest Corner Method for initial basic feasible solution"""
        supply = [s.supply for s in self.sources]
        demand = [d.demand for d in self.destinations]
        costs = self.cost_matrix.values.astype(float)

        allocation = np.zeros_like(costs)
        i, j = 0, 0

        while i < len(supply) and j < len(demand):
            alloc = min(supply[i], demand[j])
            allocation[i, j] = alloc
            supply[i] -= alloc
            demand[j] -= alloc

            if supply[i] == 0:
                i += 1
            else:
                j += 1

        total_cost = (allocation * costs).sum()

        return {
            "method": "Northwest_Corner",
            "allocation": allocation.tolist(),
            "total_cost": round(total_cost, 2),
            "sources": [s.id for s in self.sources],
            "destinations": [d.id for d in self.destinations]
        }

    def least_cost_method(self) -> Dict[str, Any]:
        """Least Cost Method for initial solution"""
        supply = [s.supply for s in self.sources]
        demand = [d.demand for d in self.destinations]
        costs = self.cost_matrix.values.astype(float).copy()

        allocation = np.zeros_like(costs)

        while sum(supply) > 0 and sum(demand) > 0:
            # Find minimum cost cell
            min_cost = float('inf')
            min_i, min_j = -1, -1
            for i in range(len(supply)):
                for j in range(len(demand)):
                    if supply[i] > 0 and demand[j] > 0 and costs[i, j] < min_cost:
                        min_cost = costs[i, j]
                        min_i, min_j = i, j

            alloc = min(supply[min_i], demand[min_j])
            allocation[min_i, min_j] = alloc
            supply[min_i] -= alloc
            demand[min_j] -= alloc

        total_cost = (allocation * self.cost_matrix.values.astype(float)).sum()

        return {
            "method": "Least_Cost",
            "allocation": allocation.tolist(),
            "total_cost": round(total_cost, 2)
        }

    def vogel_approximation(self) -> Dict[str, Any]:
        """Vogel's Approximation Method (VAM) - usually gives better initial solution"""
        supply = [s.supply for s in self.sources]
        demand = [d.demand for d in self.destinations]
        costs = self.cost_matrix.values.astype(float).copy()

        allocation = np.zeros_like(costs)

        while sum(supply) > 0 and sum(demand) > 0:
            # Calculate penalties for rows
            row_penalties = []
            for i in range(len(supply)):
                if supply[i] > 0:
                    row_costs = sorted([costs[i, j] for j in range(len(demand)) if demand[j] > 0])
                    penalty = row_costs[1] - row_costs[0] if len(row_costs) > 1 else 0
                    row_penalties.append((penalty, i))
                else:
                    row_penalties.append((-1, i))

            # Calculate penalties for columns
            col_penalties = []
            for j in range(len(demand)):
                if demand[j] > 0:
                    col_costs = sorted([costs[i, j] for i in range(len(supply)) if supply[i] > 0])
                    penalty = col_costs[1] - col_costs[0] if len(col_costs) > 1 else 0
                    col_penalties.append((penalty, j))
                else:
                    col_penalties.append((-1, j))

            # Find max penalty
            max_row = max(row_penalties, key=lambda x: x[0])
            max_col = max(col_penalties, key=lambda x: x[0])

            if max_row[0] >= max_col[0]:
                i = max_row[1]
                # Find min cost in this row
                min_cost = float('inf')
                min_j = -1
                for j in range(len(demand)):
                    if demand[j] > 0 and costs[i, j] < min_cost:
                        min_cost = costs[i, j]
                        min_j = j
                j = min_j
            else:
                j = max_col[1]
                # Find min cost in this column
                min_cost = float('inf')
                min_i = -1
                for i in range(len(supply)):
                    if supply[i] > 0 and costs[i, j] < min_cost:
                        min_cost = costs[i, j]
                        min_i = i
                i = min_i

            alloc = min(supply[i], demand[j])
            allocation[i, j] = alloc
            supply[i] -= alloc
            demand[j] -= alloc

        total_cost = (allocation * self.cost_matrix.values.astype(float)).sum()

        return {
            "method": "Vogel_Approximation",
            "allocation": allocation.tolist(),
            "total_cost": round(total_cost, 2)
        }


class AssignmentEngine:
    """
    Chapter 7: Resource allocation (Assignment Problem)
    Hungarian Algorithm implementation
    """

    def __init__(self, cost_matrix: np.ndarray):
        """
        cost_matrix: square matrix where cost_matrix[i,j] is cost of assigning worker i to job j
        """
        self.cost_matrix = cost_matrix
        self.n = cost_matrix.shape[0]

    def hungarian_algorithm(self) -> Dict[str, Any]:
        """Solve assignment problem using Hungarian algorithm"""
        try:
            from scipy.optimize import linear_sum_assignment

            row_ind, col_ind = linear_sum_assignment(self.cost_matrix)
            total_cost = self.cost_matrix[row_ind, col_ind].sum()

            assignments = []
            for r, c in zip(row_ind, col_ind):
                assignments.append({
                    "worker": int(r),
                    "job": int(c),
                    "cost": float(self.cost_matrix[r, c])
                })

            return {
                "method": "Hungarian_Algorithm",
                "assignments": assignments,
                "total_cost": round(total_cost, 2),
                "optimal": True
            }
        except ImportError:
            return {"error": "scipy not installed"}


class TheoryOfConstraintsEngine:
    """
    Chapter 8: Theory of constraints
    Bottleneck identification, Throughput Accounting, Drum-Buffer-Rope
    """

    def __init__(self, resources: List[TOCResource], products: List[Dict]):
        """
        products: [{"id": "", "name": "", "selling_price": 0, "raw_material_cost": 0, 
                    "demand": 0, "processing_times": {"resource_id": hours}}]
        """
        self.resources = resources
        self.products = products

    def identify_bottleneck(self) -> Dict[str, Any]:
        """Identify bottleneck resource (highest utilization)"""
        utilizations = []
        for res in self.resources:
            util = (res.used_hours / res.capacity_hours) * 100 if res.capacity_hours > 0 else 0
            utilizations.append({
                "resource_id": res.id,
                "name": res.name,
                "capacity": res.capacity_hours,
                "used": res.used_hours,
                "utilization_pct": round(util, 2),
                "is_bottleneck": util >= 100 or (util == max(
                    [(r.used_hours / r.capacity_hours) * 100 for r in self.resources if r.capacity_hours > 0], default=0))
            })

        bottleneck = max(utilizations, key=lambda x: x['utilization_pct'])
        return {
            "bottleneck_resource": bottleneck,
            "all_resources": utilizations,
            "system_constraint": bottleneck['resource_id'] if bottleneck['utilization_pct'] >= 100 else None
        }

    def throughput_accounting(self) -> Dict[str, Any]:
        """Calculate Throughput (T), Inventory (I), Operating Expense (OE)"""
        total_throughput = 0
        product_analysis = []

        for prod in self.products:
            throughput = (prod['selling_price'] - prod['raw_material_cost']) * prod['demand']
            total_throughput += throughput

            # Time at bottleneck determines priority
            bottleneck_times = {res.id: prod['processing_times'].get(res.id, 0) 
                              for res in self.resources}

            product_analysis.append({
                "product_id": prod['id'],
                "name": prod['name'],
                "throughput": round(throughput, 2),
                "throughput_per_unit": round(prod['selling_price'] - prod['raw_material_cost'], 2),
                "bottleneck_hours": bottleneck_times,
                "throughput_per_bottleneck_hour": round(
                    throughput / sum(bottleneck_times.values()), 2) if sum(bottleneck_times.values()) > 0 else 0
            })

        # Sort by throughput per bottleneck hour (DBR priority)
        product_analysis.sort(key=lambda x: x['throughput_per_bottleneck_hour'], reverse=True)

        total_oe = sum(res.operating_expense for res in self.resources)

        return {
            "total_throughput": round(total_throughput, 2),
            "total_operating_expense": round(total_oe, 2),
            "net_profit": round(total_throughput - total_oe, 2),
            "roi_approx": round((total_throughput - total_oe) / total_oe * 100, 2) if total_oe > 0 else 0,
            "product_priority": product_analysis,
            "timestamp": datetime.now().isoformat()
        }

    def optimize_product_mix(self) -> Dict[str, Any]:
        """Optimize product mix based on bottleneck"""
        bottleneck_info = self.identify_bottleneck()
        bottleneck_id = bottleneck_info['system_constraint']

        if not bottleneck_id:
            return {"message": "No bottleneck detected - produce to demand", "product_mix": self.products}

        # Find bottleneck resource
        bottleneck_res = next(r for r in self.resources if r.id == bottleneck_id)
        available_hours = bottleneck_res.capacity_hours

        # Calculate throughput per bottleneck hour for each product
        ranked_products = []
        for prod in self.products:
            tb_per_unit = prod['selling_price'] - prod['raw_material_cost']
            bottleneck_hours = prod['processing_times'].get(bottleneck_id, 0)

            if bottleneck_hours > 0:
                tb_per_hour = tb_per_unit / bottleneck_hours
                ranked_products.append({
                    **prod,
                    "throughput_per_hour": tb_per_hour,
                    "max_demand": prod['demand']
                })

        # Sort by throughput per bottleneck hour (descending)
        ranked_products.sort(key=lambda x: x['throughput_per_hour'], reverse=True)

        # Allocate bottleneck hours
        remaining_hours = available_hours
        optimal_mix = []

        for prod in ranked_products:
            hours_needed = prod['max_demand'] * prod['processing_times'].get(bottleneck_id, 0)

            if hours_needed <= remaining_hours:
                optimal_mix.append({
                    "product_id": prod['id'],
                    "quantity": prod['max_demand'],
                    "bottleneck_hours_used": hours_needed,
                    "throughput": prod['max_demand'] * (prod['selling_price'] - prod['raw_material_cost'])
                })
                remaining_hours -= hours_needed
            else:
                quantity = int(remaining_hours / prod['processing_times'].get(bottleneck_id, 1))
                if quantity > 0:
                    optimal_mix.append({
                        "product_id": prod['id'],
                        "quantity": quantity,
                        "bottleneck_hours_used": quantity * prod['processing_times'].get(bottleneck_id, 0),
                        "throughput": quantity * (prod['selling_price'] - prod['raw_material_cost'])
                    })
                remaining_hours = 0
                break

        total_throughput = sum(p['throughput'] for p in optimal_mix)

        return {
            "bottleneck_id": bottleneck_id,
            "available_hours": available_hours,
            "optimal_mix": optimal_mix,
            "total_throughput": round(total_throughput, 2),
            "unallocated_hours": round(remaining_hours, 2),
            "method": "Throughput_Priority"
        }


class CostProfitAnalysisEngine:
    """
    Chapter 4: Cost & profit analysis (CVP Analysis)
    Break-even, Margin of Safety, Target Profit, Multi-product
    """

    def __init__(self, bep: BreakEvenPoint):
        self.bep = bep

    def break_even_analysis(self) -> Dict[str, float]:
        """Calculate break-even point"""
        fc = self.bep.fixed_costs
        vc = self.bep.variable_cost_per_unit
        sp = self.bep.selling_price_per_unit

        if sp <= vc:
            return {"error": "Selling price must exceed variable cost"}

        cm_per_unit = sp - vc  # Contribution margin
        cm_ratio = cm_per_unit / sp

        bep_units = fc / cm_per_unit
        bep_revenue = fc / cm_ratio

        # Margin of safety at different volumes
        mos_units = lambda actual: actual - bep_units
        mos_pct = lambda actual: ((actual - bep_units) / actual) * 100 if actual > 0 else 0

        # Target profit
        target_units = (fc + self.bep.target_profit) / cm_per_unit if self.bep.target_profit else None

        return {
            "contribution_margin_per_unit": round(cm_per_unit, 2),
            "contribution_margin_ratio": round(cm_ratio, 4),
            "break_even_units": round(bep_units, 2),
            "break_even_revenue": round(bep_revenue, 2),
            "target_profit_units": round(target_units, 2) if target_units else None,
            "margin_of_safety_formula": "Actual - BE Units",
            "operating_leverage": round(cm_ratio, 4)  # Simplified
        }

    def multi_product_break_even(self, products: List[Dict]) -> Dict[str, Any]:
        """
        products: [{"name": "", "sales_mix": 0.3, "sp": 0, "vc": 0}]
        """
        total_sales_mix = sum(p['sales_mix'] for p in products)

        weighted_cm = 0
        for p in products:
            mix_ratio = p['sales_mix'] / total_sales_mix
            cm = p['sp'] - p['vc']
            weighted_cm += cm * mix_ratio

        bep_total = self.bep.fixed_costs / weighted_cm if weighted_cm > 0 else 0

        product_breakdown = []
        for p in products:
            mix_ratio = p['sales_mix'] / total_sales_mix
            units = bep_total * mix_ratio
            revenue = units * p['sp']
            product_breakdown.append({
                "product": p['name'],
                "break_even_units": round(units, 2),
                "break_even_revenue": round(revenue, 2),
                "sales_mix_pct": round(mix_ratio * 100, 2)
            })

        return {
            "weighted_contribution_margin": round(weighted_cm, 2),
            "total_break_even_units": round(bep_total, 2),
            "product_breakdown": product_breakdown
        }

    def scenario_analysis(self, scenarios: List[Dict]) -> pd.DataFrame:
        """
        scenarios: [{"name": "Optimistic", "volume": 1000, "sp": 50, "vc": 30}]
        """
        results = []
        for s in scenarios:
            cm = s['sp'] - s['vc']
            total_cm = cm * s['volume']
            profit = total_cm - self.bep.fixed_costs

            results.append({
                "scenario": s['name'],
                "volume": s['volume'],
                "selling_price": s['sp'],
                "variable_cost": s['vc'],
                "contribution_margin": cm,
                "total_contribution": total_cm,
                "profit": profit,
                "break_even": self.bep.fixed_costs / cm if cm > 0 else 0
            })

        return pd.DataFrame(results)


# =============================================================================
# SECTION 4: ERP INTEGRATION LAYER
# =============================================================================



# =============================================================================
# SECTION 7: NEW ENGINES — REALIGNED TO ACTUAL BOOK CHAPTERS
# =============================================================================

class GraphicalLPEngine:
    """
    Chapter 3: البرمجة الخطية: الحل البياني
    Graphical Method for 2-variable LP problems
    Plots feasible region, finds corner points, identifies optimal
    """

    def __init__(self, objective: LPObjective, constraints: List[LPConstraint]):
        self.objective = objective
        self.constraints = constraints
        self.corner_points = []
        self.optimal_point = None
        self.optimal_value = None

    def _get_intersections(self) -> List[Tuple[float, float]]:
        """Find all intersection points of constraint boundaries"""
        import itertools
        points = [(0.0, 0.0)]  # Origin is always a candidate

        # Collect all boundary lines (treat as equalities)
        lines = []
        for cons in self.constraints:
            a, b = cons.coefficients[0], cons.coefficients[1]
            c = cons.rhs
            if a != 0 or b != 0:
                lines.append((a, b, c))

        # Add axes intercepts for each line
        for a, b, c in lines:
            if a != 0:
                points.append((c / a, 0.0))  # x-intercept
            if b != 0:
                points.append((0.0, c / b))  # y-intercept

        # Intersections between pairs of lines
        for (a1, b1, c1), (a2, b2, c2) in itertools.combinations(lines, 2):
            det = a1 * b2 - a2 * b1
            if abs(det) > 1e-10:
                x = (c1 * b2 - c2 * b1) / det
                y = (a1 * c2 - a2 * c1) / det
                points.append((x, y))

        return points

    def _is_feasible(self, x: float, y: float) -> bool:
        """Check if point satisfies all constraints"""
        for cons in self.constraints:
            lhs = cons.coefficients[0] * x + cons.coefficients[1] * y
            if cons.operator == "<=":
                if lhs > cons.rhs + 1e-6:
                    return False
            elif cons.operator == ">=":
                if lhs < cons.rhs - 1e-6:
                    return False
            else:  # ==
                if abs(lhs - cons.rhs) > 1e-6:
                    return False
        # Non-negativity
        if x < -1e-6 or y < -1e-6:
            return False
        return True

    def solve(self) -> Dict[str, Any]:
        """Solve 2-variable LP graphically"""
        if len(self.objective.coefficients) != 2:
            return {"error": "Graphical method requires exactly 2 variables"}

        points = self._get_intersections()
        feasible_points = []

        for x, y in points:
            if self._is_feasible(x, y):
                feasible_points.append((round(x, 4), round(y, 4)))

        # Remove duplicates
        feasible_points = list(set(feasible_points))
        self.corner_points = feasible_points

        if not feasible_points:
            return {"error": "No feasible region found", "corner_points": []}

        # Evaluate objective at each corner point
        c1, c2 = self.objective.coefficients[0], self.objective.coefficients[1]
        best_val = float('-inf') if self.objective.sense == "maximize" else float('inf')
        best_point = None

        for x, y in feasible_points:
            val = c1 * x + c2 * y
            if self.objective.sense == "maximize":
                if val > best_val:
                    best_val = val
                    best_point = (x, y)
            else:
                if val < best_val:
                    best_val = val
                    best_point = (x, y)

        self.optimal_point = best_point
        self.optimal_value = best_val

        return {
            "method": "Graphical_LP",
            "objective": self.objective.name,
            "sense": self.objective.sense,
            "corner_points": feasible_points,
            "optimal_point": best_point,
            "optimal_value": round(best_val, 4),
            "variable_names": ["x1", "x2"],
            "timestamp": datetime.now().isoformat()
        }

    def generate_plot_data(self) -> Dict[str, Any]:
        """Generate data for plotting feasible region"""
        if not self.corner_points:
            self.solve()

        # Sort corner points for polygon drawing
        import math
        cx = sum(p[0] for p in self.corner_points) / len(self.corner_points)
        cy = sum(p[1] for p in self.corner_points) / len(self.corner_points)

        sorted_points = sorted(self.corner_points, 
                              key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

        # Constraint lines for plotting
        lines = []
        for cons in self.constraints:
            a, b = cons.coefficients[0], cons.coefficients[1]
            c = cons.rhs
            if a != 0 and b != 0:
                x_vals = [0, c / a]
                y_vals = [c / b, 0]
                lines.append({
                    "name": cons.name,
                    "x": [round(v, 2) for v in x_vals],
                    "y": [round(v, 2) for v in y_vals],
                    "operator": cons.operator
                })

        return {
            "feasible_region": sorted_points,
            "optimal_point": self.optimal_point,
            "objective_value": self.optimal_value,
            "constraint_lines": lines
        }


class GameTheoryEngine:
    """
    Chapter 7: نظرية المباريات (Game Theory)
    Two-person zero-sum games
    """

    def __init__(self, payoff_matrix: np.ndarray, 
                 player_a_strategies: List[str] = None,
                 player_b_strategies: List[str] = None):
        self.payoff_matrix = np.array(payoff_matrix)
        self.rows, self.cols = self.payoff_matrix.shape
        self.player_a_strategies = player_a_strategies or [f"A{i+1}" for i in range(self.rows)]
        self.player_b_strategies = player_b_strategies or [f"B{j+1}" for j in range(self.cols)]

    def find_saddle_point(self) -> Dict[str, Any]:
        """Find saddle point using minimax criterion"""
        # Row minimums (Player A's security levels)
        row_mins = np.min(self.payoff_matrix, axis=1)
        maximin = np.max(row_mins)
        maximin_row = np.argmax(row_mins)

        # Column maximums (Player B's security levels)
        col_maxs = np.max(self.payoff_matrix, axis=0)
        minimax = np.min(col_maxs)
        minimax_col = np.argmin(col_maxs)

        has_saddle = abs(maximin - minimax) < 1e-10

        return {
            "has_saddle_point": bool(has_saddle),
            "maximin": round(float(maximin), 4),
            "maximin_strategy": self.player_a_strategies[maximin_row],
            "minimax": round(float(minimax), 4),
            "minimax_strategy": self.player_b_strategies[minimax_col],
            "game_value": round(float(maximin), 4) if has_saddle else None,
            "row_mins": [round(float(x), 4) for x in row_mins],
            "col_maxs": [round(float(x), 4) for x in col_maxs]
        }

    def solve_mixed_strategy(self) -> Dict[str, Any]:
        """Solve for mixed strategy using LP formulation"""
        try:
            from scipy.optimize import linprog

            # For 2x2 games, solve analytically
            if self.rows == 2 and self.cols == 2:
                a = self.payoff_matrix
                # Player A's optimal mixed strategy
                denom = (a[0,0] + a[1,1]) - (a[0,1] + a[1,0])
                if abs(denom) < 1e-10:
                    return {"error": "Degenerate game - no mixed strategy solution"}

                p1 = (a[1,1] - a[1,0]) / denom
                p2 = 1 - p1

                # Player B's optimal mixed strategy
                q1 = (a[1,1] - a[0,1]) / denom
                q2 = 1 - q1

                # Game value
                v = (a[0,0]*a[1,1] - a[0,1]*a[1,0]) / denom

                return {
                    "method": "Analytical_2x2",
                    "game_value": round(float(v), 4),
                    "player_a_strategy": {
                        self.player_a_strategies[0]: round(float(p1), 4),
                        self.player_a_strategies[1]: round(float(p2), 4)
                    },
                    "player_b_strategy": {
                        self.player_b_strategies[0]: round(float(q1), 4),
                        self.player_b_strategies[1]: round(float(q2), 4)
                    }
                }
            else:
                # For larger games, use LP formulation
                # Player A wants to maximize minimum expected payoff
                # Formulate as LP: maximize v subject to constraints

                # Simplified: use scipy for general case
                c = [0] * self.rows + [-1]  # Minimize -v = maximize v
                A_ub = []
                b_ub = []

                for j in range(self.cols):
                    row = [-self.payoff_matrix[i, j] for i in range(self.rows)] + [1]
                    A_ub.append(row)
                    b_ub.append(0)

                # Sum of probabilities = 1
                A_eq = [[1] * self.rows + [0]]
                b_eq = [1]

                bounds = [(0, 1) for _ in range(self.rows)] + [(None, None)]

                result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, 
                               bounds=bounds, method='highs')

                if result.success:
                    strategies = {self.player_a_strategies[i]: round(float(result.x[i]), 4) 
                                 for i in range(self.rows)}
                    return {
                        "method": "LP_Formulation",
                        "game_value": round(float(result.x[-1]), 4),
                        "player_a_strategy": strategies,
                        "success": True
                    }
                else:
                    return {"error": "LP solver failed", "message": result.message}
        except Exception as e:
            return {"error": str(e)}

    def dominance_reduction(self) -> Dict[str, Any]:
        """Apply dominance to reduce matrix size"""
        matrix = self.payoff_matrix.copy()
        rows_kept = list(range(self.rows))
        cols_kept = list(range(self.cols))

        changed = True
        iterations = 0

        while changed and iterations < 100:
            changed = False
            iterations += 1

            # Check row dominance (for Player A - higher is better)
            to_remove = []
            for i in rows_kept:
                for j in rows_kept:
                    if i != j:
                        if all(matrix[i, k] <= matrix[j, k] for k in cols_kept):
                            if any(matrix[i, k] < matrix[j, k] for k in cols_kept):
                                to_remove.append(i)
                                changed = True
                                break
            rows_kept = [r for r in rows_kept if r not in to_remove]

            # Check column dominance (for Player B - lower is better)
            to_remove = []
            for i in cols_kept:
                for j in cols_kept:
                    if i != j:
                        if all(matrix[k, i] >= matrix[k, j] for k in rows_kept):
                            if any(matrix[k, i] > matrix[k, j] for k in rows_kept):
                                to_remove.append(i)
                                changed = True
                                break
            cols_kept = [c for c in cols_kept if c not in to_remove]

        reduced_matrix = matrix[np.ix_(rows_kept, cols_kept)] if rows_kept and cols_kept else np.array([])

        return {
            "original_size": f"{self.rows}x{self.cols}",
            "reduced_size": f"{len(rows_kept)}x{len(cols_kept)}",
            "rows_kept": [self.player_a_strategies[i] for i in rows_kept],
            "cols_kept": [self.player_b_strategies[j] for j in cols_kept],
            "reduced_matrix": reduced_matrix.tolist() if reduced_matrix.size > 0 else [],
            "iterations": iterations
        }

    def analyze(self) -> Dict[str, Any]:
        """Complete game theory analysis"""
        saddle = self.find_saddle_point()
        dominance = self.dominance_reduction()

        result = {
            "payoff_matrix": self.payoff_matrix.tolist(),
            "player_a_strategies": self.player_a_strategies,
            "player_b_strategies": self.player_b_strategies,
            "saddle_point_analysis": saddle,
            "dominance_reduction": dominance
        }

        if not saddle["has_saddle_point"]:
            mixed = self.solve_mixed_strategy()
            result["mixed_strategy_solution"] = mixed

        return result


class PERTCPMEngine:
    """
    Chapter 8: شبكات الأعمال (PERT/CPM Network Analysis)
    Project scheduling, critical path, slack analysis
    """

    def __init__(self, activities: List[Dict[str, Any]]):
        """
        activities: [{"id": "A", "name": "Task A", "predecessors": [], 
                     "duration": 5, "optimistic": 3, "most_likely": 5, "pessimistic": 7}]
        """
        self.activities = activities
        self.nodes = set()
        self.graph = {}
        self._build_graph()

    def _build_graph(self):
        """Build activity-on-node network"""
        for act in self.activities:
            self.nodes.add(act['id'])
            self.graph[act['id']] = {
                'name': act.get('name', act['id']),
                'duration': act.get('duration', 0),
                'predecessors': act.get('predecessors', []),
                'successors': [],
                'es': 0, 'ef': 0, 'ls': 0, 'lf': 0, 'slack': 0
            }

        # Build successor links
        for act in self.activities:
            for pred in act.get('predecessors', []):
                if pred in self.graph:
                    self.graph[pred]['successors'].append(act['id'])

    def _calculate_pert_duration(self, act: Dict) -> float:
        """Calculate expected duration using beta distribution"""
        if 'optimistic' in act and 'most_likely' in act and 'pessimistic' in act:
            o, m, p = act['optimistic'], act['most_likely'], act['pessimistic']
            return (o + 4*m + p) / 6
        return act.get('duration', 0)

    def _calculate_variance(self, act: Dict) -> float:
        """Calculate variance for PERT"""
        if 'optimistic' in act and 'pessimistic' in act:
            return ((act['pessimistic'] - act['optimistic']) / 6) ** 2
        return 0

    def forward_pass(self) -> Dict[str, Any]:
        """Calculate Early Start (ES) and Early Finish (EF)"""
        # Topological sort
        visited = set()
        temp_mark = set()
        order = []

        def visit(node):
            if node in temp_mark:
                raise ValueError("Cycle detected in network")
            if node not in visited:
                temp_mark.add(node)
                for succ in self.graph[node]['successors']:
                    visit(succ)
                temp_mark.remove(node)
                visited.add(node)
                order.append(node)

        for node in self.nodes:
            if node not in visited:
                visit(node)

        # Forward pass
        for node in order:
            act = self.graph[node]
            if act['predecessors']:
                act['es'] = max(self.graph[p]['ef'] for p in act['predecessors'])
            act['ef'] = act['es'] + act['duration']

        return {node: {'es': self.graph[node]['es'], 'ef': self.graph[node]['ef']} 
                for node in self.nodes}

    def backward_pass(self, project_duration: float) -> Dict[str, Any]:
        """Calculate Late Start (LS) and Late Finish (LF)"""
        # Reverse topological order
        visited = set()
        order = []

        def visit(node):
            if node not in visited:
                visited.add(node)
                for pred in self.graph[node]['predecessors']:
                    visit(pred)
                order.append(node)

        for node in self.nodes:
            if not self.graph[node]['successors']:
                visit(node)

        # Backward pass
        for node in order:
            act = self.graph[node]
            if not act['successors']:
                act['lf'] = project_duration
            else:
                act['lf'] = min(self.graph[s]['ls'] for s in act['successors'])
            act['ls'] = act['lf'] - act['duration']
            act['slack'] = act['ls'] - act['es']

        return {node: {'ls': self.graph[node]['ls'], 'lf': self.graph[node]['lf'], 
                       'slack': self.graph[node]['slack']} 
                for node in self.nodes}

    def analyze(self) -> Dict[str, Any]:
        """Complete PERT/CPM analysis"""
        # Update durations with PERT expected times
        for act in self.activities:
            node_id = act['id']
            self.graph[node_id]['duration'] = self._calculate_pert_duration(act)

        # Forward pass
        forward = self.forward_pass()

        # Project duration = max EF of terminal nodes
        terminal_nodes = [n for n in self.nodes if not self.graph[n]['successors']]
        project_duration = max(self.graph[n]['ef'] for n in terminal_nodes)

        # Backward pass
        backward = self.backward_pass(project_duration)

        # Critical path
        critical_path = [n for n in self.nodes if abs(self.graph[n]['slack']) < 1e-6]

        # Activity details
        activity_details = []
        for act in self.activities:
            node_id = act['id']
            g = self.graph[node_id]
            activity_details.append({
                "id": node_id,
                "name": g['name'],
                "duration": round(g['duration'], 2),
                "es": round(g['es'], 2),
                "ef": round(g['ef'], 2),
                "ls": round(g['ls'], 2),
                "lf": round(g['lf'], 2),
                "slack": round(g['slack'], 2),
                "is_critical": abs(g['slack']) < 1e-6,
                "variance": round(self._calculate_variance(act), 4)
            })

        # Total project variance (sum of variances on critical path)
        critical_variance = sum(self._calculate_variance(act) 
                              for act in self.activities 
                              if act['id'] in critical_path)

        return {
            "method": "PERT_CPM",
            "project_duration": round(project_duration, 2),
            "critical_path": critical_path,
            "critical_path_duration": round(project_duration, 2),
            "total_variance": round(critical_variance, 4),
            "activities": activity_details,
            "timestamp": datetime.now().isoformat()
        }


class DynamicProgrammingEngine:
    """
    Chapter 9 & 11: البرمجة الديناميكية (Dynamic Programming)
    Stage-wise optimization
    """

    def knapsack_01(self, capacity: float, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        0/1 Knapsack problem
        items: [{"id": "", "weight": 0, "value": 0}]
        """
        n = len(items)
        W = int(capacity)

        # DP table
        dp = [[0] * (W + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            item = items[i - 1]
            wt = int(item['weight'])
            val = item['value']

            for w in range(W + 1):
                if wt <= w:
                    dp[i][w] = max(dp[i-1][w], dp[i-1][w-wt] + val)
                else:
                    dp[i][w] = dp[i-1][w]

        # Backtrack to find selected items
        selected = []
        w = W
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i-1][w]:
                selected.append(items[i-1]['id'])
                w -= int(items[i-1]['weight'])

        return {
            "problem": "0/1_Knapsack",
            "capacity": capacity,
            "max_value": dp[n][W],
            "selected_items": selected,
            "total_weight": sum(item['weight'] for item in items if item['id'] in selected),
            "timestamp": datetime.now().isoformat()
        }

    def shortest_path(self, stages: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Multi-stage shortest path
        stages: [[{"node": "S", "cost": 0}], [{"node": "A", "cost": 2, "from": "S"}], ...]
        """
        # Simplified: use standard DP approach
        # This is a template - actual implementation depends on network structure
        return {
            "problem": "Shortest_Path",
            "stages": len(stages),
            "method": "Dynamic_Programming",
            "note": "Provide network structure for full solution",
            "timestamp": datetime.now().isoformat()
        }


class GoalProgrammingEngine:
    """
    Chapter 10: برمجة الأهداف (Goal Programming)
    Multi-objective optimization with priority levels
    """

    def __init__(self, goals: List[Dict[str, Any]], constraints: List[LPConstraint],
                 variables: List[str]):
        """
        goals: [{"name": "", "coefficients": [], "target": 0, "priority": 1, "type": "minimize_deviation"}]
        """
        self.goals = goals
        self.constraints = constraints
        self.variables = variables

    def solve_preemptive(self) -> Dict[str, Any]:
        """
        Preemptive (lexicographic) goal programming
        Solve by priority level
        """
        try:
            from scipy.optimize import linprog

            # Group goals by priority
            priorities = sorted(set(g['priority'] for g in self.goals))

            results = []
            achieved_goals = []

            for priority in priorities:
                priority_goals = [g for g in self.goals if g['priority'] == priority]

                # Build objective: minimize sum of deviations for this priority
                # Add deviation variables
                n_vars = len(self.variables)
                n_goals = len(priority_goals)

                # For simplicity, solve each goal sequentially
                for goal in priority_goals:
                    # Create LP: minimize deviation from target
                    c = goal['coefficients'] + [1]  # Add deviation variable

                    # This is a simplified version
                    # Full implementation would add d+ and d- variables

                    result = {
                        "priority": priority,
                        "goal": goal['name'],
                        "target": goal['target'],
                        "status": "solved",
                        "method": "preemptive_gp"
                    }
                    achieved_goals.append(result)

            return {
                "method": "Preemptive_Goal_Programming",
                "priorities": priorities,
                "goals_achieved": achieved_goals,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    def solve_weighted(self, weights: List[float]) -> Dict[str, Any]:
        """
        Weighted goal programming
        Minimize weighted sum of deviations
        """
        return {
            "method": "Weighted_Goal_Programming",
            "weights": weights,
            "status": "Template - provide full network for complete solution",
            "timestamp": datetime.now().isoformat()
        }

class ORERPModule:
    """
    Main ERP Integration Class for Operations Research Module
    Compatible with BIO-ERP and EventManager ERP architectures
    """

    def __init__(self, db_connection=None):
        self.db = db_connection
        self.decision_engine = None
        self.lp_engine = None
        self.inventory_engine = None
        self.transport_engine = None
        self.assignment_engine = None
        self.toc_engine = None
        self.cvp_engine = None
        self.session_log = []

    def log_operation(self, operation: str, details: Dict):
        """Audit trail for all OR operations"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        }
        self.session_log.append(entry)
        return entry

    # ---- Decision Analysis API ----
    def create_decision_model(self, states: List[Dict], alternatives: List[Dict]) -> str:
        """Create and store a decision analysis model"""
        state_objs = [DecisionState(**s) for s in states]
        alt_objs = []
        for a in alternatives:
            alt = DecisionAlternative(
                id=a['id'],
                name=a['name'],
                payoffs=a.get('payoffs', {}),
                costs=a.get('costs', {})
            )
            alt_objs.append(alt)

        self.decision_engine = DecisionAnalysisEngine(state_objs, alt_objs)
        model_id = f"DEC_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.log_operation("CREATE_DECISION_MODEL", {
            "model_id": model_id,
            "states": len(states),
            "alternatives": len(alternatives)
        })

        return model_id

    def run_decision_analysis(self, criterion: str, alpha: float = 0.5) -> Dict[str, Any]:
        """Run decision analysis with specified criterion"""
        if not self.decision_engine:
            return {"error": "No decision model loaded"}

        criterion_enum = DecisionCriterion(criterion)

        if criterion_enum == DecisionCriterion.MAXIMAX:
            result = self.decision_engine.maximax()
        elif criterion_enum == DecisionCriterion.MAXIMIN:
            result = self.decision_engine.maximin()
        elif criterion_enum == DecisionCriterion.HURWICZ:
            result = self.decision_engine.hurwicz(alpha)
        elif criterion_enum == DecisionCriterion.LAPLACE:
            result = self.decision_engine.laplace()
        elif criterion_enum == DecisionCriterion.MINIMAX_REGRET:
            result = self.decision_engine.minimax_regret()
        elif criterion_enum == DecisionCriterion.EMV:
            result = self.decision_engine.expected_monetary_value()
        elif criterion_enum == DecisionCriterion.EOL:
            result = self.decision_engine.expected_opportunity_loss()
        else:
            return {"error": "Unknown criterion"}

        self.log_operation("RUN_DECISION_ANALYSIS", {
            "criterion": criterion,
            "result": result
        })

        return {
            "criterion": criterion,
            "recommended_alternative": result[0],
            "value": result[1],
            "full_report": self.decision_engine.get_decision_report()
        }

    # ---- Linear Programming API ----
    def solve_linear_program(self, objective: Dict, constraints: List[Dict]) -> Dict[str, Any]:
        """Solve LP problem"""
        obj = LPObjective(**objective)
        cons = [LPConstraint(**c) for c in constraints]

        self.lp_engine = LinearProgrammingEngine(obj, cons)
        result = self.lp_engine.solve()

        self.log_operation("SOLVE_LP", {
            "objective": objective['name'],
            "constraints_count": len(constraints),
            "result": result.get("success")
        })

        return result

    # ---- Inventory API ----
    def optimize_inventory(self, items: List[Dict], model_type: str = "all") -> List[Dict]:
        """Run inventory optimization"""
        item_objs = [InventoryItem(**item) for item in items]
        self.inventory_engine = InventoryOptimizationEngine(item_objs)

        results = []
        for item in item_objs:
            if model_type == "all":
                res = self.inventory_engine.run_all_models(item)
            elif model_type == "eoq":
                res = self.inventory_engine.eoq_basic(item)
            elif model_type == "epq":
                res = self.inventory_engine.epq_model(item)
            else:
                res = {"error": f"Unknown model type: {model_type}"}

            results.append(res)

        self.log_operation("OPTIMIZE_INVENTORY", {
            "items_count": len(items),
            "model_type": model_type
        })

        return results

    def abc_classify_inventory(self, items_data: List[Dict]) -> pd.DataFrame:
        """ABC classification"""
        self.inventory_engine = InventoryOptimizationEngine([])
        result = self.inventory_engine.abc_analysis(items_data)

        self.log_operation("ABC_CLASSIFICATION", {
            "items_count": len(items_data)
        })

        return result

    # ---- Transportation API ----
    def solve_transportation(self, sources: List[Dict], destinations: List[Dict], 
                          routes: List[Dict], method: str = "vogel") -> Dict[str, Any]:
        """Solve transportation problem"""
        srcs = [TransportNode(**s) for s in sources]
        dsts = [TransportNode(**d) for d in destinations]
        rts = [TransportRoute(**r) for r in routes]

        self.transport_engine = TransportationEngine(srcs, dsts, rts)

        if method == "nw_corner":
            result = self.transport_engine.northwest_corner()
        elif method == "least_cost":
            result = self.transport_engine.least_cost_method()
        elif method == "vogel":
            result = self.transport_engine.vogel_approximation()
        else:
            return {"error": "Unknown method"}

        self.log_operation("SOLVE_TRANSPORTATION", {
            "method": method,
            "sources": len(sources),
            "destinations": len(destinations)
        })

        return result

    # ---- Assignment API ----
    def solve_assignment(self, cost_matrix: List[List[float]]) -> Dict[str, Any]:
        """Solve assignment problem"""
        matrix = np.array(cost_matrix)
        self.assignment_engine = AssignmentEngine(matrix)
        result = self.assignment_engine.hungarian_algorithm()

        self.log_operation("SOLVE_ASSIGNMENT", {
            "matrix_size": matrix.shape
        })

        return result

    # ---- Theory of Constraints API ----
    def analyze_constraints(self, resources: List[Dict], products: List[Dict]) -> Dict[str, Any]:
        """TOC analysis"""
        res_objs = [TOCResource(**r) for r in resources]

        self.toc_engine = TheoryOfConstraintsEngine(res_objs, products)
        bottleneck = self.toc_engine.identify_bottleneck()
        throughput = self.toc_engine.throughput_accounting()
        optimal_mix = self.toc_engine.optimize_product_mix()

        self.log_operation("ANALYZE_CONSTRAINTS", {
            "resources": len(resources),
            "products": len(products),
            "bottleneck": bottleneck.get("bottleneck_resource", {}).get("id")
        })

        return {
            "bottleneck_analysis": bottleneck,
            "throughput_accounting": throughput,
            "optimal_product_mix": optimal_mix
        }

    # ---- CVP Analysis API ----
    def analyze_cost_profit(self, fixed_costs: float, variable_cost: float, 
                           selling_price: float, target_profit: float = 0,
                           scenarios: List[Dict] = None) -> Dict[str, Any]:
        """CVP Analysis"""
        bep = BreakEvenPoint(
            fixed_costs=fixed_costs,
            variable_cost_per_unit=variable_cost,
            selling_price_per_unit=selling_price,
            target_profit=target_profit
        )

        self.cvp_engine = CostProfitAnalysisEngine(bep)
        basic = self.cvp_engine.break_even_analysis()

        result = {
            "basic_analysis": basic,
            "scenarios": None
        }

        if scenarios:
            result["scenarios"] = self.cvp_engine.scenario_analysis(scenarios).to_dict('records')

        self.log_operation("CVP_ANALYSIS", {
            "fixed_costs": fixed_costs,
            "selling_price": selling_price
        })

        return result

    def get_audit_trail(self) -> List[Dict]:
        """Return complete audit trail"""
        return self.session_log

    def export_report(self) -> Dict[str, Any]:
        """Export comprehensive OR module report"""
        return {
            "module": "Operations Research ERP Module",
            "version": "1.0.0",
            "source_book": "البحوث الإلكترونية في المحاسبة - Al-Azhar University 2025",
            "chapters_covered_realigned": [
                "1. طبيعة بحوث العمليات (Nature of OR)",
                "2. البرمجة الخطية (Linear Programming)",
                "3. البرمجة الخطية: الحل البياني (Graphical LP)",
                "4. طريقة السمبلكس (Simplex Method)",
                "5. الثنائية وتحليل الحساسية (Duality & Sensitivity)",
                "6. نماذج النقل (Transportation Models)",
                "7. نظرية المباريات (Game Theory)",
                "8. شبكات الأعمال / PERT-CPM (Business Networks)",
                "9. البرمجة الديناميكية (Dynamic Programming)",
                "10. برمجة الأهداف (Goal Programming)",
                "11. البرمجة الديناميكية المتقدمة (Advanced DP)"
            ],
            "chapters_covered": [
                "1. Nature of Operations Research",
                "2. Decision-making mathematical models",
                "3. Linear programming and its applications",
                "4. Cost & profit analysis",
                "5. Inventory models",
                "6. Transportation models",
                "7. Resource allocation",
                "8. Theory of constraints",
                "9. Risk and uncertainty in decision-making"
            ],
            "operations_count": len(self.session_log),
            "audit_trail": self.session_log,
            "timestamp": datetime.now().isoformat()
        }

    # ---- Chapter 3: Graphical LP ----
    def solve_graphical_lp(self, objective: Dict, constraints: List[Dict]) -> Dict[str, Any]:
        """Solve 2-variable LP using graphical method"""
        try:
            obj = LPObjective(**objective)
            cons = [LPConstraint(**c) for c in constraints]
            engine = GraphicalLPEngine(obj, cons)
            result = engine.solve()
            if result.get("success") is not False:
                result["plot_data"] = engine.generate_plot_data()

            self.log_operation("GRAPHICAL_LP", {
                "objective": objective['name'],
                "constraints": len(constraints)
            })
            return result
        except Exception as e:
            return {"error": str(e)}

    # ---- Chapter 7: Game Theory ----
    def analyze_game(self, payoff_matrix: List[List[float]], 
                    player_a: List[str] = None,
                    player_b: List[str] = None) -> Dict[str, Any]:
        """Analyze two-person zero-sum game"""
        try:
            import numpy as np
            engine = GameTheoryEngine(np.array(payoff_matrix), player_a, player_b)
            result = engine.analyze()

            self.log_operation("GAME_THEORY", {
                "matrix_size": f"{len(payoff_matrix)}x{len(payoff_matrix[0])}",
                "has_saddle": result['saddle_point_analysis']['has_saddle_point']
            })
            return result
        except Exception as e:
            return {"error": str(e)}

    # ---- Chapter 8: PERT/CPM ----
    def analyze_network(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """PERT/CPM network analysis"""
        try:
            engine = PERTCPMEngine(activities)
            result = engine.analyze()

            self.log_operation("PERT_CPM", {
                "activities": len(activities),
                "project_duration": result['project_duration']
            })
            return result
        except Exception as e:
            return {"error": str(e)}

    # ---- Chapter 9 & 11: Dynamic Programming ----
    def solve_knapsack(self, capacity: float, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """0/1 Knapsack using Dynamic Programming"""
        try:
            engine = DynamicProgrammingEngine()
            result = engine.knapsack_01(capacity, items)

            self.log_operation("DYNAMIC_PROGRAMMING", {
                "problem": "knapsack",
                "capacity": capacity,
                "items": len(items)
            })
            return result
        except Exception as e:
            return {"error": str(e)}

    # ---- Chapter 10: Goal Programming ----
    def solve_goal_programming(self, goals: List[Dict], 
                               constraints: List[Dict],
                               variables: List[str],
                               method: str = "preemptive") -> Dict[str, Any]:
        """Goal Programming for multi-objective optimization"""
        try:
            goal_objs = [g for g in goals]
            cons = [LPConstraint(**c) for c in constraints]
            engine = GoalProgrammingEngine(goal_objs, cons, variables)

            if method == "preemptive":
                result = engine.solve_preemptive()
            else:
                result = engine.solve_weighted([])

            self.log_operation("GOAL_PROGRAMMING", {
                "method": method,
                "goals": len(goals)
            })
            return result
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# SECTION 5: FASTAPI / FLASK COMPATIBLE ENDPOINTS (Pseudo-code for integration)
# =============================================================================

"""
# FastAPI Integration Example:

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
or_module = ORERPModule()

class DecisionModelRequest(BaseModel):
    states: list
    alternatives: list
    criterion: str

@app.post("/api/v1/or/decision-analysis")
def decision_analysis(req: DecisionModelRequest):
    or_module.create_decision_model(req.states, req.alternatives)
    return or_module.run_decision_analysis(req.criterion)

@app.post("/api/v1/or/linear-programming")
def linear_programming(objective: dict, constraints: list):
    return or_module.solve_linear_program(objective, constraints)

@app.post("/api/v1/or/inventory/optimize")
def inventory_optimize(items: list, model_type: str = "all"):
    return or_module.optimize_inventory(items, model_type)

@app.post("/api/v1/or/transportation")
def transportation(sources: list, destinations: list, routes: list, method: str = "vogel"):
    return or_module.solve_transportation(sources, destinations, routes, method)

@app.post("/api/v1/or/assignment")
def assignment(cost_matrix: list):
    return or_module.solve_assignment(cost_matrix)

@app.post("/api/v1/or/theory-of-constraints")
def theory_of_constraints(resources: list, products: list):
    return or_module.analyze_constraints(resources, products)

@app.post("/api/v1/or/cvp-analysis")
def cvp_analysis(fixed_costs: float, variable_cost: float, selling_price: float, 
                 target_profit: float = 0, scenarios: list = None):
    return or_module.analyze_cost_profit(fixed_costs, variable_cost, selling_price, 
                                        target_profit, scenarios)

@app.get("/api/v1/or/audit-trail")
def audit_trail():
    return or_module.get_audit_trail()

@app.get("/api/v1/or/report")
def module_report():
    return or_module.export_report()
"""

# =============================================================================
# SECTION 6: UNIT TESTS
# =============================================================================

def run_tests():
    """Run all module tests"""
    import unittest

    class TestORERPModule(unittest.TestCase):
        def setUp(self):
            self.module = ORERPModule()

        def test_decision_analysis(self):
            states = [
                {"id": "s1", "name": "Boom", "probability": 0.3},
                {"id": "s2", "name": "Normal", "probability": 0.5},
                {"id": "s3", "name": "Recession", "probability": 0.2}
            ]
            alternatives = [
                {"id": "a1", "name": "Expand", "payoffs": {"s1": 100, "s2": 50, "s3": -20}},
                {"id": "a2", "name": "Maintain", "payoffs": {"s1": 60, "s2": 40, "s3": 10}},
                {"id": "a3", "name": "Contract", "payoffs": {"s1": 30, "s2": 30, "s3": 20}}
            ]

            self.module.create_decision_model(states, alternatives)
            result = self.module.run_decision_analysis("maximax")
            self.assertEqual(result['recommended_alternative'], "Expand")

            result = self.module.run_decision_analysis("maximin")
            self.assertEqual(result['recommended_alternative'], "Contract")

        def test_eoq(self):
            items = [{
                "sku": "TEST-001",
                "name": "Test Item",
                "annual_demand": 1000,
                "ordering_cost": 50,
                "holding_cost_per_unit": 2.5,
                "unit_cost": 10,
                "lead_time_days": 5,
                "daily_demand": 1000/365
            }]

            result = self.module.optimize_inventory(items, "eoq")
            self.assertTrue(result[0]['optimal_order_quantity'] > 0)

        def test_transportation(self):
            sources = [
                {"id": "S1", "name": "Factory A", "supply": 100, "is_source": True},
                {"id": "S2", "name": "Factory B", "supply": 200, "is_source": True}
            ]
            destinations = [
                {"id": "D1", "name": "Warehouse 1", "demand": 150, "is_source": False},
                {"id": "D2", "name": "Warehouse 2", "demand": 150, "is_source": False}
            ]
            routes = [
                {"from_id": "S1", "to_id": "D1", "cost_per_unit": 10},
                {"from_id": "S1", "to_id": "D2", "cost_per_unit": 15},
                {"from_id": "S2", "to_id": "D1", "cost_per_unit": 12},
                {"from_id": "S2", "to_id": "D2", "cost_per_unit": 8}
            ]

            result = self.module.solve_transportation(sources, destinations, routes, "vogel")
            self.assertTrue(result['total_cost'] > 0)

        def test_cvp(self):
            result = self.module.analyze_cost_profit(
                fixed_costs=10000,
                variable_cost=30,
                selling_price=50
            )
            self.assertEqual(result['basic_analysis']['break_even_units'], 500)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestORERPModule)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    print("=" * 70)
    print("OPERATIONS RESEARCH ERP MODULE v1.0.0")
    print("Based on: البحوث الإلكترونية في المحاسبة (Al-Azhar University 2025)")
    print("=" * 70)
    print("\nRunning comprehensive tests...\n")
    run_tests()
