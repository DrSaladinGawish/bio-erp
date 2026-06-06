"""
intelligence/or/__init__.py
Operations Research engines for IHE-ERP (lightweight, in-memory).
6 engines: LP, EOQ, PERT, Profit, BreakEven, Forecast.
"""
from __future__ import annotations
import logging
import math
import statistics
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("incentivehouse_organ.intelligence.or")


# 1. Linear Programming (simple 2-product model solved by enumeration)
def solve_lp(products: list, constraints: dict) -> dict:
    """
    Solve a simple 2-product LP by enumeration.
    products: list of {name, profit_per_unit, resource_a_per_unit, resource_b_per_unit}
    constraints: {resource_a: max, resource_b: max}
    Returns optimal {x1, x2, profit}.
    """
    if len(products) < 1:
        return {"engine": "lp", "status": "error", "error": "no products"}
    p1, p2 = (products + [{}] * 2)[:2]
    a, b = constraints.get("resource_a", 100), constraints.get("resource_b", 100)
    best = {"x1": 0, "x2": 0, "profit": 0.0}
    step = 1
    x1_max = int(a / max(p1.get("resource_a_per_unit", 1), 0.001))
    x2_max = int(b / max(p2.get("resource_b_per_unit", 1) if p2 else 1, 0.001))
    for x1 in range(0, min(x1_max, 200), step):
        for x2 in range(0, min(x2_max, 200), step):
            ra = x1 * p1.get("resource_a_per_unit", 0) + x2 * p2.get("resource_a_per_unit", 0)
            rb = x1 * p1.get("resource_b_per_unit", 0) + x2 * p2.get("resource_b_per_unit", 0)
            if ra <= a and rb <= b:
                profit = x1 * p1.get("profit_per_unit", 0) + x2 * p2.get("profit_per_unit", 0)
                if profit > best["profit"]:
                    best = {"x1": x1, "x2": x2, "profit": profit}
    return {
        "engine": "lp",
        "status": "ok",
        "optimal_x1": best["x1"],
        "optimal_x2": best["x2"],
        "max_profit": round(best["profit"], 2),
        "generated_at": datetime.now().isoformat(),
    }


# 2. Economic Order Quantity
def solve_eoq(demand_annual: float, order_cost: float, holding_cost: float) -> dict:
    """EOQ = sqrt(2 * D * S / H)"""
    if holding_cost <= 0:
        return {"engine": "eoq", "status": "error", "error": "holding_cost must be > 0"}
    eoq = math.sqrt(2 * demand_annual * order_cost / holding_cost)
    orders_per_year = demand_annual / eoq if eoq else 0
    cycle_time_days = 365 / orders_per_year if orders_per_year else 0
    return {
        "engine": "eoq",
        "status": "ok",
        "eoq": round(eoq, 2),
        "orders_per_year": round(orders_per_year, 2),
        "cycle_time_days": round(cycle_time_days, 1),
        "total_cost": round(math.sqrt(2 * demand_annual * order_cost * holding_cost), 2),
        "generated_at": datetime.now().isoformat(),
    }


# 3. PERT (3-point estimate: optimistic, most-likely, pessimistic)
def solve_pert(tasks: list) -> dict:
    """
    tasks: list of {name, o, m, p} (optimistic, most-likely, pessimistic)
    Returns expected time and critical path (longest).
    """
    expected = []
    for t in tasks:
        e = (t.get("o", 0) + 4 * t.get("m", 0) + t.get("p", 0)) / 6
        var = ((t.get("p", 0) - t.get("o", 0)) / 6) ** 2
        expected.append({"name": t.get("name", "?"), "expected": round(e, 2), "variance": round(var, 2)})
    if not expected:
        return {"engine": "pert", "status": "error", "error": "no tasks"}
    critical = max(expected, key=lambda x: x["expected"])
    return {
        "engine": "pert",
        "status": "ok",
        "tasks": expected,
        "critical_path": critical["name"],
        "project_duration": round(critical["expected"], 2),
        "generated_at": datetime.now().isoformat(),
    }


# 4. Profit maximization (P = R - C, given revenue and cost)
def solve_profit(revenue: float, costs: dict) -> dict:
    total_cost = sum(v for v in costs.values() if isinstance(v, (int, float)))
    profit = revenue - total_cost
    margin = (profit / revenue * 100) if revenue > 0 else 0
    return {
        "engine": "profit",
        "status": "ok",
        "revenue": round(revenue, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin, 2),
        "cost_breakdown": costs,
        "generated_at": datetime.now().isoformat(),
    }


# 5. Break-even point
def solve_breakeven(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> dict:
    if price_per_unit <= variable_cost_per_unit:
        return {"engine": "breakeven", "status": "error", "error": "price must exceed variable cost"}
    units = fixed_costs / (price_per_unit - variable_cost_per_unit)
    revenue = units * price_per_unit
    return {
        "engine": "breakeven",
        "status": "ok",
        "fixed_costs": round(fixed_costs, 2),
        "price_per_unit": round(price_per_unit, 2),
        "variable_cost_per_unit": round(variable_cost_per_unit, 2),
        "contribution_margin": round(price_per_unit - variable_cost_per_unit, 2),
        "breakeven_units": round(units, 1),
        "breakeven_revenue": round(revenue, 2),
        "generated_at": datetime.now().isoformat(),
    }


# 6. Forecast (simple moving average + trend)
def solve_forecast(history: list, horizon: int = 7, window: int = 7) -> dict:
    if not history:
        return {"engine": "forecast", "status": "error", "error": "no history"}
    recent = history[-window:] if len(history) >= window else history
    avg = statistics.mean(recent) if recent else 0
    if len(history) >= 2:
        first_half = statistics.mean(history[:len(history) // 2]) if history[:len(history) // 2] else 0
        second_half = statistics.mean(history[len(history) // 2:]) if history[len(history) // 2:] else 0
        trend = second_half - first_half
    else:
        trend = 0
    forecast = [max(0.0, avg + trend * (i + 1) / 2) for i in range(horizon)]
    return {
        "engine": "forecast",
        "status": "ok",
        "history_points": len(history),
        "moving_average": round(avg, 2),
        "trend": round(trend, 2),
        "forecast": [round(x, 2) for x in forecast],
        "generated_at": datetime.now().isoformat(),
    }


# Master entrypoint
def run_or_solver(db: Session, engine: str = "all", params: dict = None) -> dict:
    """Run a single OR engine or all six."""
    params = params or {}
    result = {"version": "2.3.0", "generated_at": datetime.now().isoformat()}
    if engine in ("lp", "all"):
        try:
            result["lp"] = solve_lp(
                params.get("products", [
                    {"name": "A", "profit_per_unit": 30, "resource_a_per_unit": 2, "resource_b_per_unit": 1},
                    {"name": "B", "profit_per_unit": 40, "resource_a_per_unit": 1, "resource_b_per_unit": 2},
                ]),
                params.get("constraints", {"resource_a": 100, "resource_b": 100}),
            )
        except Exception as e:
            result["lp"] = {"status": "error", "error": str(e)}
    if engine in ("eoq", "all"):
        try:
            result["eoq"] = solve_eoq(
                params.get("demand_annual", 10000),
                params.get("order_cost", 50),
                params.get("holding_cost", 2),
            )
        except Exception as e:
            result["eoq"] = {"status": "error", "error": str(e)}
    if engine in ("pert", "all"):
        try:
            result["pert"] = solve_pert(params.get("tasks", [
                {"name": "Plan", "o": 1, "m": 3, "p": 5},
                {"name": "Design", "o": 2, "m": 4, "p": 8},
                {"name": "Build", "o": 5, "m": 10, "p": 20},
            ]))
        except Exception as e:
            result["pert"] = {"status": "error", "error": str(e)}
    if engine in ("profit", "all"):
        try:
            result["profit"] = solve_profit(
                params.get("revenue", 100000),
                params.get("costs", {"cogs": 60000, "salaries": 20000, "rent": 5000}),
            )
        except Exception as e:
            result["profit"] = {"status": "error", "error": str(e)}
    if engine in ("breakeven", "all"):
        try:
            result["breakeven"] = solve_breakeven(
                params.get("fixed_costs", 50000),
                params.get("price_per_unit", 100),
                params.get("variable_cost_per_unit", 60),
            )
        except Exception as e:
            result["breakeven"] = {"status": "error", "error": str(e)}
    if engine in ("forecast", "all"):
        try:
            # Try to fetch from DB; fall back to sample
            try:
                rows = db.execute(text("""
                    SELECT COALESCE(total_amount, 0) FROM sales_invoice
                    WHERE total_amount IS NOT NULL ORDER BY invoice_date DESC LIMIT 30
                """)).fetchall()
                hist = [float(r[0]) for r in reversed(rows)]
            except Exception:
                hist = params.get("history", [100, 110, 105, 120, 115, 130, 125])
            result["forecast"] = solve_forecast(hist, params.get("horizon", 7))
        except Exception as e:
            result["forecast"] = {"status": "error", "error": str(e)}
    return result
