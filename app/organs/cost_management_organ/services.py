"""
Cost Management Services — 24 Techniques with Real Business Logic
BIO-ERP v5.3.0 — cost_management_organ
"""



class ABCEngine:
    """1. Activity-Based Costing"""

    @staticmethod
    def calculate_activity_rate(total_cost: float, driver_quantity: float) -> float:
        if driver_quantity <= 0:
            return 0.0
        return round(total_cost / driver_quantity, 6)

    @staticmethod
    def allocate_to_product(
        pool_cost: float, total_driver_qty: float, product_consumption: float
    ) -> float:
        if total_driver_qty <= 0:
            return 0.0
        rate = pool_cost / total_driver_qty
        return round(product_consumption * rate, 4)

    @staticmethod
    def full_analysis(pools: list, allocations: list) -> dict:
        rates = {}
        for p in pools:
            rate = ABCEngine.calculate_activity_rate(
                p["total_cost"], p["total_driver_quantity"]
            )
            rates[p["pool_name"]] = {
                "rate": rate,
                "total_cost": p["total_cost"],
                "driver_quantity": p["total_driver_quantity"],
                "cost_category": p["cost_category"],
            }

        product_costs = {}
        for a in allocations:
            pname = a["product_name"]
            pool_name = a["pool_name"]
            if pname not in product_costs:
                product_costs[pname] = {"allocations": [], "total": 0.0}
            allocated = ABCEngine.allocate_to_product(
                rates[pool_name]["rate"] * rates[pool_name]["driver_quantity"],
                rates[pool_name]["driver_quantity"],
                a["consumption_quantity"],
            )
            product_costs[pname]["allocations"].append(
                {
                    "pool": pool_name,
                    "rate": rates[pool_name]["rate"],
                    "consumption": a["consumption_quantity"],
                    "allocated_cost": allocated,
                }
            )
            product_costs[pname]["total"] += allocated

        for pname in product_costs:
            product_costs[pname]["total"] = round(product_costs[pname]["total"], 4)

        total_indirect = sum(p["total_cost"] for p in pools)
        return {
            "activity_rates": rates,
            "product_costs": product_costs,
            "total_indirect_cost": round(total_indirect, 4),
        }


class TDABCEngine:
    """2. Time-Driven Activity-Based Costing"""

    @staticmethod
    def calculate_practical_capacity(
        total_cost: float,
        resources_count: int,
        days_per_year: int = 250,
        hours_per_day: int = 8,
        efficiency_pct: float = 85.0,
    ) -> dict:
        theoretical = resources_count * days_per_year * hours_per_day * 60
        practical = int(theoretical * efficiency_pct / 100.0)
        cost_per_min = total_cost / practical if practical > 0 else 0
        return {
            "theoretical_minutes": theoretical,
            "practical_minutes": practical,
            "cost_per_minute": round(cost_per_min, 6),
            "cost_per_hour": round(cost_per_min * 60, 4),
        }

    @staticmethod
    def calculate_product_cost(
        total_cost: float,
        resources_count: int,
        volume: int,
        time_per_unit_minutes: float,
        days_per_year: int = 250,
        hours_per_day: int = 8,
        efficiency_pct: float = 85.0,
    ) -> dict:
        metrics = TDABCEngine.calculate_practical_capacity(
            total_cost, resources_count, days_per_year, hours_per_day, efficiency_pct
        )
        unit_cost = time_per_unit_minutes * metrics["cost_per_minute"]
        total_cost_product = volume * unit_cost
        return {
            **metrics,
            "volume": volume,
            "time_per_unit_minutes": time_per_unit_minutes,
            "unit_cost": round(unit_cost, 6),
            "total_product_cost": round(total_cost_product, 4),
        }

    @staticmethod
    def calculate_idle_capacity(
        total_cost: float,
        resources_count: int,
        used_minutes: float,
        efficiency_pct: float = 85.0,
    ) -> dict:
        metrics = TDABCEngine.calculate_practical_capacity(
            total_cost, resources_count, efficiency_pct=efficiency_pct
        )
        practical = metrics["practical_minutes"]
        if used_minutes < practical:
            idle = practical - used_minutes
            idle_cost = idle * metrics["cost_per_minute"]
            vtype = "IDLE_CAPACITY"
        elif used_minutes > practical:
            idle = 0
            idle_cost = 0
            vtype = "CAPACITY_DEFICIT"
        else:
            idle = 0
            idle_cost = 0
            vtype = "BALANCED"
        return {
            **metrics,
            "used_minutes": round(used_minutes, 2),
            "idle_minutes": round(idle, 2),
            "idle_cost": round(idle_cost, 4),
            "utilization_pct": round(
                (used_minutes / practical * 100) if practical > 0 else 0, 2
            ),
            "variance_type": vtype,
        }


class RCAEngine:
    """3. Resource Consumption Accounting"""

    @staticmethod
    def calculate_total_cost(fixed_cost: float, proportional_cost: float) -> float:
        return round(fixed_cost + proportional_cost, 4)

    @staticmethod
    def calculate_cost_per_unit(total_cost: float, units: float) -> float:
        if units <= 0:
            return 0.0
        return round(total_cost / units, 6)

    @staticmethod
    def calculate_utilization(planned: float, actual: float) -> float:
        if planned <= 0:
            return 0.0
        return round(actual / planned * 100, 2)

    @staticmethod
    def capacity_analysis(resources: list, planned_output: float, actual_output: float) -> dict:
        resource_results = []
        total_fixed = 0.0
        total_proportional = 0.0
        for r in resources:
            total = r["fixed_cost"] + r["proportional_cost"]
            cost_per_unit = RCAEngine.calculate_cost_per_unit(total, planned_output)
            resource_results.append({
                "resource_name": r["resource_name"],
                "fixed_cost": r["fixed_cost"],
                "proportional_cost": r["proportional_cost"],
                "total_cost": total,
                "cost_per_unit": cost_per_unit,
                "output_unit": r.get("measurable_output_unit", "units"),
            })
            total_fixed += r["fixed_cost"]
            total_proportional += r["proportional_cost"]

        total_cost = total_fixed + total_proportional
        utilization = RCAEngine.calculate_utilization(planned_output, actual_output)
        capacity_cost = 0.0
        if utilization < 100:
            idle_pct = 100 - utilization
            capacity_cost = round(total_fixed * idle_pct / 100, 4)

        return {
            "resources": resource_results,
            "total_fixed_cost": round(total_fixed, 4),
            "total_proportional_cost": round(total_proportional, 4),
            "total_cost": round(total_cost, 4),
            "planned_output": planned_output,
            "actual_output": actual_output,
            "utilization_pct": utilization,
            "idle_capacity_cost": capacity_cost,
        }


class TraditionalCostingEngine:
    """4. Traditional (Volume-Based) Costing"""

    @staticmethod
    def calculate_rate(total_overhead: float, base_quantity: float) -> float:
        if base_quantity <= 0:
            return 0.0
        return round(total_overhead / base_quantity, 6)

    @staticmethod
    def allocate(
        total_overhead: float,
        base_quantity: float,
        product_consumption: float,
    ) -> float:
        rate = TraditionalCostingEngine.calculate_rate(total_overhead, base_quantity)
        return round(product_consumption * rate, 4)

    @staticmethod
    def full_analysis(
        pool_name: str,
        total_overhead: float,
        base_name: str,
        base_quantity: float,
        product_name: str,
        product_consumption: float,
    ) -> dict:
        rate = TraditionalCostingEngine.calculate_rate(total_overhead, base_quantity)
        allocated = TraditionalCostingEngine.allocate(
            total_overhead, base_quantity, product_consumption
        )
        return {
            "pool_name": pool_name,
            "allocation_base": base_name,
            "total_overhead": total_overhead,
            "base_quantity": base_quantity,
            "predetermined_rate": rate,
            "product_name": product_name,
            "product_consumption": product_consumption,
            "allocated_cost": allocated,
        }


class TargetCostingEngine:
    """5. Target Costing"""

    @staticmethod
    def calculate_target_cost(market_price: float, profit_pct: float) -> dict:
        profit_amount = market_price * profit_pct / 100
        target_cost = market_price - profit_amount
        return {
            "market_price": market_price,
            "target_profit_pct": profit_pct,
            "target_profit_amount": round(profit_amount, 4),
            "target_cost": round(target_cost, 4),
        }

    @staticmethod
    def cost_gap(current_cost: float, target_cost: float) -> dict:
        gap = current_cost - target_cost
        gap_pct = round(gap / target_cost * 100, 2) if target_cost > 0 else 0
        return {
            "current_cost": current_cost,
            "target_cost": target_cost,
            "cost_gap": round(gap, 4),
            "gap_pct": gap_pct,
            "achievable": gap <= 0,
        }

    @staticmethod
    def summary(
        product_name: str,
        market_price: float,
        profit_pct: float,
        sheets: list,
    ) -> dict:
        target = TargetCostingEngine.calculate_target_cost(market_price, profit_pct)
        total_as_is = sum(s["as_is_cost"] for s in sheets)
        total_target = sum(s["target_cost"] for s in sheets)
        gap = TargetCostingEngine.cost_gap(total_as_is, total_target)
        components = []
        for s in sheets:
            comp_gap = s["as_is_cost"] - s["target_cost"]
            components.append({
                "component": s["cost_component"],
                "as_is": s["as_is_cost"],
                "target": s["target_cost"],
                "gap": round(comp_gap, 4),
                "gap_pct": round(
                    comp_gap / s["target_cost"] * 100 if s["target_cost"] > 0 else 0, 2
                ),
            })
        return {
            "product_name": product_name,
            **target,
            "total_current_cost": round(total_as_is, 4),
            "total_target_cost": round(total_target, 4),
            "overall_gap": gap,
            "components": components,
            "status": "ACHIEVABLE" if gap["achievable"] else "GAP_REMAINS",
        }


class KaizenCostingEngine:
    """6. Kaizen Costing"""

    @staticmethod
    def calculate_reduction_path(
        current_cost: float, target_reduction_pct: float, months: int
    ) -> list:
        path = []
        monthly_rate = target_reduction_pct / 100 / months
        cost = current_cost
        for m in range(1, months + 1):
            reduction = cost * monthly_rate
            new_cost = cost - reduction
            path.append({
                "month": m,
                "cost": round(new_cost, 4),
                "reduction": round(reduction, 4),
                "cumulative_reduction_pct": round(
                    (current_cost - new_cost) / current_cost * 100, 2
                ),
            })
            cost = new_cost
        return path

    @staticmethod
    def period_analysis(
        baseline_cost: float, current_cost: float, period_number: int
    ) -> dict:
        reduction = baseline_cost - current_cost
        reduction_pct = round(reduction / baseline_cost * 100, 2) if baseline_cost > 0 else 0
        return {
            "baseline_cost": baseline_cost,
            "current_cost": current_cost,
            "period_number": period_number,
            "absolute_reduction": round(reduction, 4),
            "reduction_pct": reduction_pct,
            "monthly_avg_reduction": round(
                reduction / period_number if period_number > 0 else 0, 4
            ),
            "on_track": reduction_pct >= 0,
        }


class LifeCycleCostingEngine:
    """7. Life Cycle Costing"""

    @staticmethod
    def npv_analysis(phases: list, discount_rate_pct: float) -> dict:
        r = discount_rate_pct / 100
        total_cost = 0.0
        total_revenue = 0.0
        discounted_cashflows = []
        cumulative_cost = 0.0
        year = 0
        for p in phases:
            years = p.get("duration_years", 1)
            for y in range(int(years)):
                year += 1
                df = 1 / ((1 + r) ** year)
                annual_cost = p["cost"] / years
                annual_rev = p.get("revenue", 0) / years
                dc_cost = annual_cost * df
                dc_rev = annual_rev * df
                cumulative_cost += annual_cost
                discounted_cashflows.append({
                    "year": year,
                    "phase": p["phase"],
                    "undiscounted_cost": round(annual_cost, 4),
                    "undiscounted_revenue": round(annual_rev, 4),
                    "discount_factor": round(df, 6),
                    "discounted_cost": round(dc_cost, 4),
                    "discounted_revenue": round(dc_rev, 4),
                    "cumulative_undiscounted": round(cumulative_cost, 4),
                })
                total_cost += dc_cost
                total_revenue += dc_rev
        total_profit = total_revenue - total_cost
        roi = round(total_profit / total_cost * 100, 2) if total_cost > 0 else 0
        return {
            "discount_rate_pct": discount_rate_pct,
            "total_npv_cost": round(total_cost, 4),
            "total_npv_revenue": round(total_revenue, 4),
            "npv_profit": round(total_profit, 4),
            "roi_pct": roi,
            "total_years": year,
            "phases_detail": discounted_cashflows,
        }


class ThroughputAccountingEngine:
    """8. Throughput Accounting"""

    @staticmethod
    def calculate_throughput(selling_price: float, material_cost: float) -> float:
        return round(selling_price - material_cost, 4)

    @staticmethod
    def throughput_per_bottleneck_minute(
        throughput: float, bottleneck_minutes: float
    ) -> float:
        if bottleneck_minutes <= 0:
            return 0.0
        return round(throughput / bottleneck_minutes, 6)

    @staticmethod
    def ranking_analysis(
        products: list, total_opex: float, bottleneck_available: float
    ) -> dict:
        ranked = []
        total_throughput = 0.0
        for p in products:
            tp = ThroughputAccountingEngine.calculate_throughput(
                p["selling_price"], p["material_cost"]
            )
            tp_per_min = ThroughputAccountingEngine.throughput_per_bottleneck_minute(
                tp, p["bottleneck_time_minutes"]
            )
            product_tp = tp * p["units_sold"]
            total_throughput += product_tp
            ranked.append({
                "product_name": p["product_name"],
                "unit_throughput": tp,
                "total_throughput": round(product_tp, 4),
                "bottleneck_minutes_per_unit": p["bottleneck_time_minutes"],
                "throughput_per_bottleneck_minute": tp_per_min,
                "units_sold": p["units_sold"],
            })

        ranked.sort(key=lambda x: x["throughput_per_bottleneck_minute"], reverse=True)
        for i, r in enumerate(ranked):
            r["priority_rank"] = i + 1

        net_profit = total_throughput - total_opex
        rot = round(net_profit / total_opex * 100, 2) if total_opex > 0 else 0
        total_bottleneck_used = sum(
            p["bottleneck_time_minutes"] * p["units_sold"] for p in products
        )
        return {
            "product_ranking": ranked,
            "total_throughput": round(total_throughput, 4),
            "total_operating_expenses": total_opex,
            "net_profit": round(net_profit, 4),
            "return_on_throughput_pct": rot,
            "bottleneck_minutes_used": round(total_bottleneck_used, 2),
            "bottleneck_minutes_available": bottleneck_available,
            "bottleneck_utilization_pct": round(
                total_bottleneck_used / bottleneck_available * 100
                if bottleneck_available > 0
                else 0,
                2,
            ),
        }


class StandardCostingEngine:
    """9. Standard Costing"""

    @staticmethod
    def calculate_variances(items: list) -> list:
        results = []
        for item in items:
            price_var = (item["actual_price"] - item["standard_price"]) * item[
                "actual_quantity"
            ]
            qty_var = (item["actual_quantity"] - item["standard_quantity"]) * item[
                "standard_price"
            ]
            efficiency_var = (item["actual_quantity"] - item["standard_quantity"]) * item[
                "standard_price"
            ]
            spending_var = (item["actual_price"] - item["standard_price"]) * item[
                "actual_quantity"
            ]
            total_var = price_var + qty_var
            results.append({
                "item_name": item["item_name"],
                "standard_quantity": item["standard_quantity"],
                "actual_quantity": item["actual_quantity"],
                "standard_price": item["standard_price"],
                "actual_price": item["actual_price"],
                "price_variance": round(price_var, 4),
                "quantity_variance": round(qty_var, 4),
                "efficiency_variance": round(efficiency_var, 4),
                "spending_variance": round(spending_var, 4),
                "total_variance": round(total_var, 4),
                "is_favorable": total_var <= 0,
            })
        return results

    @staticmethod
    def overhead_variances(
        budgeted_overhead: float,
        actual_overhead: float,
        budgeted_base: float,
        actual_base: float,
    ) -> dict:
        if budgeted_base <= 0:
            rate = 0
        else:
            rate = budgeted_overhead / budgeted_base
        applied = rate * actual_base
        spending_var = actual_overhead - budgeted_overhead
        efficiency_var = budgeted_overhead - applied
        volume_var = applied - budgeted_overhead
        total_var = actual_overhead - applied
        return {
            "predetermined_rate": round(rate, 6),
            "budgeted_overhead": budgeted_overhead,
            "actual_overhead": actual_overhead,
            "applied_overhead": round(applied, 4),
            "spending_variance": round(spending_var, 4),
            "efficiency_variance": round(efficiency_var, 4),
            "volume_variance": round(volume_var, 4),
            "total_overhead_variance": round(total_var, 4),
        }


class VariableCostingEngine:
    """10. Variable Costing"""

    @staticmethod
    def contribution_margin(selling_price: float, variable_cost: float) -> float:
        return round(selling_price - variable_cost, 4)

    @staticmethod
    def contribution_margin_ratio(
        selling_price: float, variable_cost: float
    ) -> float:
        if selling_price <= 0:
            return 0.0
        return round((selling_price - variable_cost) / selling_price * 100, 2)

    @staticmethod
    def break_even_units(fixed_cost: float, contribution_margin: float) -> float:
        if contribution_margin <= 0:
            return float("inf")
        return round(fixed_cost / contribution_margin, 2)

    @staticmethod
    def break_even_revenue(
        fixed_cost: float, contribution_margin_ratio: float
    ) -> float:
        if contribution_margin_ratio <= 0:
            return float("inf")
        return round(fixed_cost / (contribution_margin_ratio / 100), 4)

    @staticmethod
    def target_units(fixed_cost: float, target_profit: float, cm: float) -> float:
        if cm <= 0:
            return float("inf")
        return round((fixed_cost + target_profit) / cm, 2)

    @staticmethod
    def income_statement(
        selling_price: float,
        variable_cost: float,
        fixed_cost: float,
        units_sold: int,
        beginning_inventory: int = 0,
        units_produced: int = 0,
        ending_inventory: int = 0,
    ) -> dict:
        if units_produced == 0:
            units_produced = units_sold + ending_inventory - beginning_inventory
        cm = VariableCostingEngine.contribution_margin(selling_price, variable_cost)
        cm_ratio = VariableCostingEngine.contribution_margin_ratio(
            selling_price, variable_cost
        )
        revenue = selling_price * units_sold
        total_variable = variable_cost * units_sold
        contribution = revenue - total_variable
        net_income = contribution - fixed_cost
        return {
            "revenue": round(revenue, 4),
            "variable_cost_per_unit": variable_cost,
            "total_variable_cost": round(total_variable, 4),
            "contribution_margin": round(contribution, 4),
            "contribution_margin_per_unit": cm,
            "contribution_margin_ratio": cm_ratio,
            "fixed_cost": fixed_cost,
            "net_income": round(net_income, 4),
            "break_even_units": VariableCostingEngine.break_even_units(fixed_cost, cm),
            "margin_of_safety_pct": round(
                (units_sold - VariableCostingEngine.break_even_units(fixed_cost, cm))
                / units_sold * 100
                if units_sold > 0
                else 0,
                2,
            ),
        }


class AbsorptionCostingEngine:
    """11. Absorption Costing"""

    @staticmethod
    def unit_product_cost(
        dm: float, dl: float, voh: float, total_foh: float, units_produced: int
    ) -> float:
        if units_produced <= 0:
            return 0.0
        foh_per_unit = total_foh / units_produced
        return round(dm + dl + voh + foh_per_unit, 4)

    @staticmethod
    def income_statement(
        selling_price: float,
        dm_per_unit: float,
        dl_per_unit: float,
        voh_per_unit: float,
        total_foh: float,
        units_produced: int,
        units_sold: int,
    ) -> dict:
        foh_per_unit = total_foh / units_produced if units_produced > 0 else 0
        product_cost = dm_per_unit + dl_per_unit + voh_per_unit + foh_per_unit
        revenue = selling_price * units_sold
        cogs = product_cost * units_sold
        gross_profit = revenue - cogs
        ending_inventory_units = units_produced - units_sold
        ending_inventory_value = product_cost * ending_inventory_units
        fixed_in_ending = foh_per_unit * ending_inventory_units
        return {
            "unit_product_cost": round(product_cost, 4),
            "foh_per_unit": round(foh_per_unit, 4),
            "revenue": round(revenue, 4),
            "cogs": round(cogs, 4),
            "gross_profit": round(gross_profit, 4),
            "gross_margin_pct": round(
                gross_profit / revenue * 100 if revenue > 0 else 0, 2
            ),
            "ending_inventory_units": ending_inventory_units,
            "ending_inventory_value": round(ending_inventory_value, 4),
            "fixed_in_inventory": round(fixed_in_ending, 4),
        }


class MarginalCostingEngine:
    """12. Marginal Costing"""

    @staticmethod
    def breakeven_analysis(
        selling_price: float, variable_cost: float, fixed_cost: float
    ) -> dict:
        cm = selling_price - variable_cost
        cm_ratio = cm / selling_price * 100 if selling_price > 0 else 0
        be_units = fixed_cost / cm if cm > 0 else float("inf")
        be_revenue = fixed_cost / (cm_ratio / 100) if cm_ratio > 0 else float("inf")
        return {
            "contribution_margin_per_unit": round(cm, 4),
            "contribution_margin_ratio": round(cm_ratio, 2),
            "break_even_units": round(be_units, 2),
            "break_even_revenue": round(be_revenue, 4),
        }

    @staticmethod
    def target_profit_analysis(
        selling_price: float,
        variable_cost: float,
        fixed_cost: float,
        target_profit: float,
    ) -> dict:
        cm = selling_price - variable_cost
        if cm <= 0:
            units_needed = float("inf")
        else:
            units_needed = (fixed_cost + target_profit) / cm
        return {
            "target_profit": target_profit,
            "units_needed": round(units_needed, 2),
            "revenue_needed": round(units_needed * selling_price, 4),
            "contribution_margin_per_unit": round(cm, 4),
        }

    @staticmethod
    def full_analysis(
        selling_price: float,
        variable_cost: float,
        fixed_cost: float,
        target_profit: float,
        units_sold: int,
    ) -> dict:
        be = MarginalCostingEngine.breakeven_analysis(
            selling_price, variable_cost, fixed_cost
        )
        tp = MarginalCostingEngine.target_profit_analysis(
            selling_price, variable_cost, fixed_cost, target_profit
        )
        revenue = selling_price * units_sold
        total_variable = variable_cost * units_sold
        contribution = revenue - total_variable
        net_income = contribution - fixed_cost
        mo_safety = (
            (units_sold - be["break_even_units"]) / units_sold * 100
            if units_sold > 0
            else 0
        )
        dol = contribution / net_income if net_income > 0 else float("inf")
        return {
            "breakeven": be,
            "target_profit": tp,
            "income": {
                "revenue": round(revenue, 4),
                "total_variable_cost": round(total_variable, 4),
                "contribution_margin": round(contribution, 4),
                "fixed_cost": fixed_cost,
                "net_income": round(net_income, 4),
            },
            "margin_of_safety_pct": round(mo_safety, 2),
            "degree_of_operating_leverage": round(dol, 4) if dol != float("inf") else "inf",
        }


class ProcessCostingEngine:
    """13. Process Costing"""

    @staticmethod
    def calculate_equivalent_units(
        units_completed: int, ending_wip_units: int, pct_complete: float
    ) -> float:
        wip_equivalent = ending_wip_units * pct_complete / 100
        return round(units_completed + wip_equivalent, 2)

    @staticmethod
    def cost_per_equivalent_unit(total_cost: float, equivalent_units: float) -> float:
        if equivalent_units <= 0:
            return 0.0
        return round(total_cost / equivalent_units, 6)

    @staticmethod
    def process_departments(departments: list) -> dict:
        results = []
        cumulative_cost = 0.0
        cumulative_units = 0
        for dept in departments:
            direct = dept["direct_material"] + dept["direct_labor"] + dept["overhead"]
            total_in = cumulative_cost + direct
            equiv_units = ProcessCostingEngine.calculate_equivalent_units(
                dept["units_completed"],
                dept["ending_wip_units"],
                dept["ending_wip_pct_complete"],
            )
            cost_per_eu = ProcessCostingEngine.cost_per_equivalent_unit(
                total_in, equiv_units
            )
            cost_transferred = dept["units_completed"] * cost_per_eu
            cost_ending_wip = equiv_units * cost_per_eu - cost_transferred
            results.append({
                "department": dept["department_name"],
                "direct_material": dept["direct_material"],
                "direct_labor": dept["direct_labor"],
                "overhead": dept["overhead"],
                "total_added_this_dept": round(direct, 4),
                "cost_from_prior_dept": round(cumulative_cost, 4),
                "total_cost_in_dept": round(total_in, 4),
                "equivalent_units": equiv_units,
                "cost_per_equivalent_unit": cost_per_eu,
                "cost_transferred_out": round(cost_transferred, 4),
                "cost_ending_wip": round(cost_ending_wip, 4),
            })
            cumulative_cost = round(cost_transferred, 4)
            cumulative_units = dept["units_completed"]
        final_unit_cost = (
            cumulative_cost / cumulative_units if cumulative_units > 0 else 0
        )
        return {
            "product_name": "Process Costing Analysis",
            "departments": results,
            "total_cost_accounted_for": round(cumulative_cost, 4),
            "total_units_completed": cumulative_units,
            "final_cost_per_unit": round(final_unit_cost, 4),
        }


class JobOrderCostingEngine:
    """14. Job Order Costing"""

    @staticmethod
    def calculate_job_cost(
        direct_material: float,
        direct_labor_hours: float,
        labor_rate: float,
        overhead_rate: float,
    ) -> dict:
        direct_labor = direct_labor_hours * labor_rate
        overhead_applied = overhead_rate * (direct_labor_hours * labor_rate)
        total = direct_material + direct_labor + overhead_applied
        return {
            "direct_material": direct_material,
            "direct_labor": round(direct_labor, 4),
            "direct_labor_hours": direct_labor_hours,
            "labor_rate": labor_rate,
            "overhead_applied": round(overhead_applied, 4),
            "overhead_rate": overhead_rate,
            "total_job_cost": round(total, 4),
        }

    @staticmethod
    def job_profitability(
        job_number: str,
        customer_name: str,
        quantity: int,
        direct_material: float,
        direct_labor_hours: float,
        labor_rate: float,
        overhead_rate: float,
        quoted_price: float,
    ) -> dict:
        cost = JobOrderCostingEngine.calculate_job_cost(
            direct_material, direct_labor_hours, labor_rate, overhead_rate
        )
        unit_cost = cost["total_job_cost"] / quantity if quantity > 0 else 0
        profit = quoted_price - cost["total_job_cost"]
        margin = (
            profit / quoted_price * 100 if quoted_price > 0 else 0
        )
        return {
            "job_number": job_number,
            "customer_name": customer_name,
            "quantity": quantity,
            **cost,
            "unit_cost": round(unit_cost, 4),
            "quoted_price": quoted_price,
            "profit": round(profit, 4),
            "profit_margin_pct": round(margin, 2),
            "status": "PROFITABLE" if profit > 0 else "LOSS",
        }


class BatchCostingEngine:
    """15. Batch Costing"""

    @staticmethod
    def calculate_batch_cost(
        direct_material: float,
        direct_labor: float,
        batch_overhead: float,
        batch_size: int,
    ) -> dict:
        total = direct_material + direct_labor + batch_overhead
        unit_cost = total / batch_size if batch_size > 0 else 0
        return {
            "direct_material": direct_material,
            "direct_labor": direct_labor,
            "batch_overhead": batch_overhead,
            "total_batch_cost": round(total, 4),
            "batch_size": batch_size,
            "cost_per_unit": round(unit_cost, 4),
        }


class ContractCostingEngine:
    """16. Contract Costing"""

    @staticmethod
    def percentage_of_completion(
        contract_value: float,
        estimated_total_cost: float,
        costs_to_date: float,
        progress_billing: float = 0,
    ) -> dict:
        if estimated_total_cost <= 0:
            pct = 0.0
        else:
            pct = costs_to_date / estimated_total_cost * 100
        revenue_recognized = contract_value * pct / 100
        estimated_profit = contract_value - estimated_total_cost
        profit_recognized = estimated_profit * pct / 100
        cost_to_complete = estimated_total_cost - costs_to_date
        return {
            "contract_value": contract_value,
            "estimated_total_cost": estimated_total_cost,
            "costs_to_date": costs_to_date,
            "percentage_complete": round(pct, 2),
            "revenue_recognized": round(revenue_recognized, 4),
            "estimated_profit": round(estimated_profit, 4),
            "profit_recognized": round(profit_recognized, 4),
            "cost_to_complete": round(cost_to_complete, 4),
            "progress_billing": progress_billing,
            "billing_excess": round(progress_billing - revenue_recognized, 4),
            "billings_on_cip": "DEBIT" if progress_billing > revenue_recognized else "CREDIT",
        }


class ServiceCostingEngine:
    """17. Service Costing"""

    @staticmethod
    def calculate_service_cost(
        direct_labor_cost: float,
        direct_labor_hours: float,
        overhead_cost: float,
        support_staff_cost: float,
        other_direct_costs: float,
        service_units_delivered: int,
    ) -> dict:
        total = (
            direct_labor_cost
            + overhead_cost
            + support_staff_cost
            + other_direct_costs
        )
        cost_per_unit = total / service_units_delivered if service_units_delivered > 0 else 0
        cost_per_hour = (
            total / direct_labor_hours if direct_labor_hours > 0 else 0
        )
        return {
            "direct_labor_cost": direct_labor_cost,
            "overhead_cost": overhead_cost,
            "support_staff_cost": support_staff_cost,
            "other_direct_costs": other_direct_costs,
            "total_service_cost": round(total, 4),
            "service_units_delivered": service_units_delivered,
            "cost_per_unit": round(cost_per_unit, 4),
            "cost_per_hour": round(cost_per_hour, 4),
        }

    @staticmethod
    def profitability(
        service_name: str,
        direct_labor_cost: float,
        direct_labor_hours: float,
        overhead_cost: float,
        support_staff_cost: float,
        other_direct_costs: float,
        service_units_delivered: int,
        billing_rate: float,
    ) -> dict:
        cost = ServiceCostingEngine.calculate_service_cost(
            direct_labor_cost,
            direct_labor_hours,
            overhead_cost,
            support_staff_cost,
            other_direct_costs,
            service_units_delivered,
        )
        revenue = billing_rate * service_units_delivered
        profit = revenue - cost["total_service_cost"]
        margin = profit / revenue * 100 if revenue > 0 else 0
        return {
            "service_name": service_name,
            **cost,
            "billing_rate": billing_rate,
            "revenue": round(revenue, 4),
            "profit": round(profit, 4),
            "profit_margin_pct": round(margin, 2),
            "status": "PROFITABLE" if profit > 0 else "LOSS",
        }


class JointProductCostingEngine:
    """18. Joint Product Costing"""

    @staticmethod
    def split_by_sales_value(joint_cost: float, products: list) -> dict:
        total_sales = sum(p["quantity"] * p["selling_price_per_unit"] for p in products)
        allocations = []
        for p in products:
            sales_value = p["quantity"] * p["selling_price_per_unit"]
            pct = sales_value / total_sales if total_sales > 0 else 0
            allocated = joint_cost * pct
            unit_cost = allocated / p["quantity"] if p["quantity"] > 0 else 0
            allocations.append({
                "product_name": p["product_name"],
                "quantity": p["quantity"],
                "selling_price_per_unit": p["selling_price_per_unit"],
                "sales_value": round(sales_value, 4),
                "allocation_pct": round(pct * 100, 2),
                "allocated_joint_cost": round(allocated, 4),
                "cost_per_unit": round(unit_cost, 4),
            })
        return {
            "method": "SALES_VALUE",
            "joint_cost": joint_cost,
            "total_sales_value": round(total_sales, 4),
            "allocations": allocations,
        }

    @staticmethod
    def split_by_physical_units(joint_cost: float, products: list) -> dict:
        total_units = sum(p["quantity"] for p in products)
        allocations = []
        for p in products:
            pct = p["quantity"] / total_units if total_units > 0 else 0
            allocated = joint_cost * pct
            unit_cost = allocated / p["quantity"] if p["quantity"] > 0 else 0
            allocations.append({
                "product_name": p["product_name"],
                "quantity": p["quantity"],
                "allocation_pct": round(pct * 100, 2),
                "allocated_joint_cost": round(allocated, 4),
                "cost_per_unit": round(unit_cost, 4),
            })
        return {
            "method": "PHYSICAL_UNITS",
            "joint_cost": joint_cost,
            "total_units": total_units,
            "allocations": allocations,
        }

    @staticmethod
    def split_by_constant_gross_margin(joint_cost: float, products: list) -> dict:
        total_revenue = sum(p["quantity"] * p["selling_price_per_unit"] for p in products)
        overall_margin = (total_revenue - joint_cost) / total_revenue if total_revenue > 0 else 0
        allocations = []
        for p in products:
            sales = p["quantity"] * p["selling_price_per_unit"]
            allowable_cost = sales * (1 - overall_margin)
            unit_cost = allowable_cost / p["quantity"] if p["quantity"] > 0 else 0
            allocations.append({
                "product_name": p["product_name"],
                "quantity": p["quantity"],
                "sales_value": round(sales, 4),
                "allowable_cost": round(allowable_cost, 4),
                "cost_per_unit": round(unit_cost, 4),
            })
        return {
            "method": "CONSTANT_GROSS_MARGIN",
            "joint_cost": joint_cost,
            "overall_gross_margin_pct": round(overall_margin * 100, 2),
            "allocations": allocations,
        }

    @staticmethod
    def full_analysis(joint_cost: float, products: list, method: str) -> dict:
        if method == "PHYSICAL_UNITS":
            return JointProductCostingEngine.split_by_physical_units(joint_cost, products)
        elif method == "CONSTANT_GROSS_MARGIN":
            return JointProductCostingEngine.split_by_constant_gross_margin(
                joint_cost, products
            )
        return JointProductCostingEngine.split_by_sales_value(joint_cost, products)


class ByProductCostingEngine:
    """19. By-Product Costing"""

    @staticmethod
    def nrv_method(
        joint_cost: float,
        main_product_name: str,
        main_quantity: int,
        main_price: float,
        by_products: list,
    ) -> dict:
        total_by_product_nrv = 0.0
        bp_details = []
        for bp in by_products:
            nrv = bp["quantity"] * bp["selling_price_per_unit"] - bp["separable_cost"]
            total_by_product_nrv += nrv
            bp_details.append({
                "product_name": bp["product_name"],
                "quantity": bp["quantity"],
                "gross_revenue": round(bp["quantity"] * bp["selling_price_per_unit"], 4),
                "separable_cost": bp["separable_cost"],
                "net_realizable_value": round(nrv, 4),
            })
        main_product_cost = joint_cost - total_by_product_nrv
        main_revenue = main_quantity * main_price
        main_profit = main_revenue - main_product_cost
        main_unit_cost = main_product_cost / main_quantity if main_quantity > 0 else 0
        return {
            "method": "NET_REALIZABLE_VALUE",
            "joint_cost": joint_cost,
            "total_by_product_nrv": round(total_by_product_nrv, 4),
            "by_products": bp_details,
            "main_product": {
                "product_name": main_product_name,
                "quantity": main_quantity,
                "price": main_price,
                "allocated_cost": round(main_product_cost, 4),
                "cost_per_unit": round(main_unit_cost, 4),
                "revenue": round(main_revenue, 4),
                "profit": round(main_profit, 4),
            },
        }

    @staticmethod
    def no_allocation_method(
        joint_cost: float,
        main_product_name: str,
        main_quantity: int,
        main_price: float,
        by_products: list,
    ) -> dict:
        bp_details = []
        total_by_rev = 0.0
        for bp in by_products:
            rev = bp["quantity"] * bp["selling_price_per_unit"]
            total_by_rev += rev
            bp_details.append({
                "product_name": bp["product_name"],
                "quantity": bp["quantity"],
                "revenue": round(rev, 4),
            })
        main_revenue = main_quantity * main_price
        main_unit_cost = joint_cost / main_quantity if main_quantity > 0 else 0
        return {
            "method": "NO_ALLOCATION",
            "joint_cost": joint_cost,
            "all_joint_cost_to_main": True,
            "by_products": bp_details,
            "total_by_product_revenue": round(total_by_rev, 4),
            "main_product": {
                "product_name": main_product_name,
                "quantity": main_quantity,
                "price": main_price,
                "allocated_cost": round(joint_cost, 4),
                "cost_per_unit": round(main_unit_cost, 4),
                "revenue": round(main_revenue, 4),
                "profit": round(main_revenue - joint_cost, 4),
            },
        }


class BackflushCostingEngine:
    """20. Backflush Costing"""

    @staticmethod
    def calculate(
        quantity_produced: int,
        bom_components: list,
        labor_rate_per_hour: float,
        labor_hours_per_unit: float,
        overhead_rate_per_unit: float,
    ) -> dict:
        total_material = 0.0
        components = []
        for comp in bom_components:
            comp_cost = comp["standard_qty_per_unit"] * comp["standard_cost_per_unit"] * quantity_produced
            total_material += comp_cost
            components.append({
                "component": comp["component_name"],
                "qty_per_unit": comp["standard_qty_per_unit"],
                "cost_per_unit": comp["standard_cost_per_unit"],
                "total_cost": round(comp_cost, 4),
            })
        total_labor = labor_rate_per_hour * labor_hours_per_unit * quantity_produced
        total_overhead = overhead_rate_per_unit * quantity_produced
        total_backflushed = total_material + total_labor + total_overhead
        unit_cost = total_backflushed / quantity_produced if quantity_produced > 0 else 0
        return {
            "quantity_produced": quantity_produced,
            "material_backflushed": round(total_material, 4),
            "labor_backflushed": round(total_labor, 4),
            "overhead_backflushed": round(total_overhead, 4),
            "total_backflushed": round(total_backflushed, 4),
            "cost_per_unit": round(unit_cost, 4),
            "components": components,
        }


class GembaCostingEngine:
    """21. Gemba Costing"""

    WASTE_COST_MULTIPLIERS = {
        "OVERPRODUCTION": 1.0,
        "WAITING": 0.8,
        "TRANSPORT": 0.6,
        "OVERPROCESSING": 0.7,
        "INVENTORY": 0.9,
        "MOTION": 0.5,
        "DEFECTS": 1.2,
    }

    @staticmethod
    def analyze_observations(
        observations: list,
        total_operating_hours: float,
        hourly_labor_rate: float,
        monthly_revenue: float,
    ) -> dict:
        total_cost_impact = 0.0
        total_time_lost = 0.0
        waste_summary = {}
        for obs in observations:
            wtype = obs["waste_type"]
            cost = obs["estimated_cost_impact"]
            time_lost = obs.get("time_lost_minutes", 0)
            total_cost_impact += cost
            total_time_lost += time_lost
            if wtype not in waste_summary:
                waste_summary[wtype] = {"count": 0, "total_cost": 0, "total_time": 0}
            waste_summary[wtype]["count"] += 1
            waste_summary[wtype]["total_cost"] += cost
            waste_summary[wtype]["total_time"] += time_lost
        for wtype in waste_summary:
            waste_summary[wtype]["total_cost"] = round(
                waste_summary[wtype]["total_cost"], 4
            )
            waste_summary[wtype]["total_time"] = round(
                waste_summary[wtype]["total_time"], 2
            )
        time_cost = total_time_lost / 60 * hourly_labor_rate
        total_waste = total_cost_impact + time_cost
        waste_pct = (
            total_waste / monthly_revenue * 100 if monthly_revenue > 0 else 0
        )
        ranked_waste = sorted(
            waste_summary.items(), key=lambda x: x[1]["total_cost"], reverse=True
        )
        return {
            "total_observations": len(observations),
            "total_direct_cost_impact": round(total_cost_impact, 4),
            "total_time_lost_minutes": round(total_time_lost, 2),
            "time_cost_impact": round(time_cost, 4),
            "total_waste_cost": round(total_waste, 4),
            "waste_as_pct_revenue": round(waste_pct, 2),
            "waste_by_type": waste_summary,
            "top_waste": [
                {"type": w[0], **w[1]} for w in ranked_waste[:5]
            ],
            "recommendations": [
                f"Focus on {w[0]} waste — highest cost impact at {w[1]['total_cost']:.2f}"
                for w in ranked_waste[:3]
            ],
        }


class QualityCostingEngine:
    """22. Quality Costing (COQ)"""

    @staticmethod
    def calculate_coq(data: dict) -> dict:
        prevention = data.get("prevention_cost", 0)
        appraisal = data.get("appliance_cost", 0)
        internal_failure = data.get("internal_failure_cost", 0)
        external_failure = data.get("external_failure_cost", 0)
        total_coq = prevention + appraisal + internal_failure + external_failure
        revenue = data.get("revenue", 0)
        total_units = data.get("total_units_produced", 0)
        defective = data.get("defective_units", 0)
        coq_ratio = total_coq / revenue * 100 if revenue > 0 else 0
        defect_rate = defective / total_units * 100 if total_units > 0 else 0
        prevention_ratio = prevention / total_coq * 100 if total_coq > 0 else 0
        failure_ratio = (internal_failure + external_failure) / total_coq * 100 if total_coq > 0 else 0
        return {
            "prevention_cost": prevention,
            "appraisal_cost": appraisal,
            "internal_failure_cost": internal_failure,
            "external_failure_cost": external_failure,
            "total_coq": round(total_coq, 4),
            "coq_to_revenue_pct": round(coq_ratio, 2),
            "defect_rate_pct": round(defect_rate, 2),
            "prevention_share_pct": round(prevention_ratio, 2),
            "failure_share_pct": round(failure_ratio, 2),
            "quality_status": (
                "EXCELLENT"
                if defect_rate < 1
                else "GOOD"
                if defect_rate < 3
                else "NEEDS_IMPROVEMENT"
            ),
            "recommendation": (
                "Invest in prevention to reduce failure costs"
                if failure_ratio > 50
                else "Quality costs are well balanced"
            ),
        }


class EnvironmentalCostingEngine:
    """23. Environmental Costing"""

    @staticmethod
    def full_analysis(data: dict) -> dict:
        waste = data.get("waste_disposal_cost", 0)
        emission = data.get("emission_treatment_cost", 0)
        compliance = data.get("compliance_cost", 0)
        remediation = data.get("remediation_cost", 0)
        prevention = data.get("prevention_cost", 0)
        carbon_tonnes = data.get("carbon_tonnes", 0)
        carbon_price = data.get("carbon_price_per_tonne", 0)
        revenue = data.get("revenue", 0)
        waste_tonnes = data.get("waste_tonnes", 0)
        carbon_cost = carbon_tonnes * carbon_price
        total_direct = waste + emission + compliance + remediation
        total_environmental = total_direct + carbon_cost
        env_ratio = total_environmental / revenue * 100 if revenue > 0 else 0
        waste_intensity = waste_tonnes / revenue * 1_000_000 if revenue > 0 else 0
        carbon_intensity = carbon_tonnes / revenue * 1_000_000 if revenue > 0 else 0
        return {
            "waste_disposal_cost": waste,
            "emission_treatment_cost": emission,
            "compliance_cost": compliance,
            "remediation_cost": remediation,
            "prevention_cost": prevention,
            "carbon_cost": round(carbon_cost, 4),
            "total_direct_environmental": round(total_direct, 4),
            "total_environmental_cost": round(total_environmental, 4),
            "environmental_cost_to_revenue_pct": round(env_ratio, 2),
            "carbon_tonnes": carbon_tonnes,
            "carbon_cost_per_tonne": carbon_price,
            "waste_tonnes": waste_tonnes,
            "waste_intensity": round(waste_intensity, 4),
            "carbon_intensity": round(carbon_intensity, 4),
            "status": (
                "LOW_RISK"
                if env_ratio < 2
                else "MODERATE_RISK"
                if env_ratio < 5
                else "HIGH_RISK"
            ),
        }


class StrategicCostManagementEngine:
    """24. Strategic Cost Management"""

    @staticmethod
    def analyze_initiative(initiative: dict) -> dict:
        current = initiative["current_cost"]
        target = initiative["target_cost"]
        impl_cost = initiative.get("implementation_cost", 0)
        payback_months = initiative.get("payback_months", 12)
        savings = current - target
        net_benefit = savings - impl_cost
        annual_savings = savings * 12
        annual_roi = (
            annual_savings / impl_cost * 100 if impl_cost > 0 else float("inf")
        )
        return {
            "initiative_name": initiative["initiative_name"],
            "technique": initiative["technique"],
            "current_cost": current,
            "target_cost": target,
            "projected_monthly_savings": round(savings, 4),
            "projected_annual_savings": round(annual_savings, 4),
            "implementation_cost": impl_cost,
            "net_benefit": round(net_benefit, 4),
            "payback_months": payback_months,
            "annual_roi_pct": round(annual_roi, 2),
            "feasibility": (
                "HIGH"
                if net_benefit > 0 and payback_months <= 12
                else "MEDIUM"
                if net_benefit > 0
                else "LOW"
            ),
        }

    @staticmethod
    def full_analysis(
        organization: str,
        initiatives: list,
        total_budget: float,
        planning_horizon_years: int,
    ) -> dict:
        analyzed = []
        total_savings = 0.0
        total_impl = 0.0
        for init in initiatives:
            result = StrategicCostManagementEngine.analyze_initiative(init)
            analyzed.append(result)
            total_savings += result["projected_annual_savings"]
            total_impl += result["implementation_cost"]
        total_net_benefit = total_savings - total_impl
        portfolio_roi = (
            total_savings / total_impl * 100 if total_impl > 0 else 0
        )
        high_priority = [a for a in analyzed if a["feasibility"] == "HIGH"]
        budget_utilization = total_impl / total_budget * 100 if total_budget > 0 else 0
        return {
            "organization": organization,
            "planning_horizon_years": planning_horizon_years,
            "total_initiatives": len(analyzed),
            "total_projected_annual_savings": round(total_savings, 4),
            "total_implementation_cost": round(total_impl, 4),
            "total_net_benefit": round(total_net_benefit, 4),
            "portfolio_roi_pct": round(portfolio_roi, 2),
            "budget_utilization_pct": round(budget_utilization, 2),
            "high_priority_count": len(high_priority),
            "initiatives": analyzed,
            "strategic_recommendation": (
                "Strong portfolio — proceed with high-priority initiatives"
                if len(high_priority) >= len(analyzed) * 0.5
                else "Review medium/low feasibility initiatives"
            ),
        }
