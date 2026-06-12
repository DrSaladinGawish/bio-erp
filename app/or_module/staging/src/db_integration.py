"""
OR-ERP Database Integration Layer
==================================
Connects OR-ERP engines to PostgreSQL for persistent storage.
Usage: from db_integration import ORDBIntegratedModule
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

# SQLAlchemy imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import OR engines
from or_erp_module import ORERPModule
from models import (
    ORDatabaseManager, generate_id, save_decision_analysis, 
    save_lp_result, save_audit_log,
    ORDecisionModel, ORLPModel, ORInventoryPolicy, ORTransportPlan,
    ORGameTheory, ORPERTCPM, ORKnapsack, ORGoalProgramming, ORCVPModel,
    ORAuditTrail
)

class ORDBIntegratedModule(ORERPModule):
    """
    OR-ERP Module with PostgreSQL persistence.
    Extends base ORERPModule to save all results to database.
    """

    def __init__(self, database_url: str = None):
        super().__init__(db_connection=None)

        # Database connection
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            "postgresql://or_erp:or_erp_secret@localhost:5433/or_erp_db"
        )
        self.db_manager = ORDatabaseManager(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.db_manager.engine)

        # Ensure tables exist
        self.db_manager.create_tables()

    @contextmanager
    def get_db(self):
        """Context manager for database sessions"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # =================================================================
    # OVERRIDDEN METHODS WITH DB PERSISTENCE
    # =================================================================

    def run_decision_analysis(self, criterion: str, alpha: float = 0.5) -> Dict[str, Any]:
        """Run decision analysis and save to DB"""
        result = super().run_decision_analysis(criterion, alpha)

        with self.get_db() as db:
            model_id = save_decision_analysis(db, result, user_id="system")
            save_audit_log(db, "RUN_DECISION_ANALYSIS", "decision", {
                "model_id": model_id,
                "criterion": criterion,
                "result": result.get("recommended_alternative")
            })
            result["saved_model_id"] = model_id

        return result

    def solve_linear_program(self, objective: Dict, constraints: List[Dict]) -> Dict[str, Any]:
        """Solve LP and save to DB"""
        result = super().solve_linear_program(objective, constraints)

        if result.get("success"):
            with self.get_db() as db:
                model_id = save_lp_result(db, result, objective.get("name", "LP Model"), user_id="system")
                save_audit_log(db, "SOLVE_LP", "linear_programming", {
                    "model_id": model_id,
                    "objective_value": result.get("objective_value"),
                    "status": result.get("status")
                })
                result["saved_model_id"] = model_id

        return result

    def solve_graphical_lp(self, objective: Dict, constraints: List[Dict]) -> Dict[str, Any]:
        """Solve graphical LP and save to DB"""
        result = super().solve_graphical_lp(objective, constraints)

        with self.get_db() as db:
            model_id = generate_id("GLP")
            glp_model = ORLPModel(
                id=model_id,
                model_name="Graphical LP",
                objective_function=objective,
                constraints=constraints,
                variable_count=2,
                constraint_count=len(constraints),
                solution=result.get("optimal_point"),
                objective_value=result.get("optimal_value"),
                solve_status="success" if "error" not in result else "failed"
            )
            db.add(glp_model)
            db.commit()
            save_audit_log(db, "GRAPHICAL_LP", "graphical_lp", {
                "model_id": model_id,
                "optimal_value": result.get("optimal_value")
            })
            result["saved_model_id"] = model_id

        return result

    def analyze_game(self, payoff_matrix: List[List[float]], 
                    player_a: List[str] = None, 
                    player_b: List[str] = None) -> Dict[str, Any]:
        """Analyze game and save to DB"""
        result = super().analyze_game(payoff_matrix, player_a, player_b)

        with self.get_db() as db:
            model_id = generate_id("GT")
            saddle = result.get("saddle_point_analysis", {})
            gt_model = ORGameTheory(
                id=model_id,
                model_name="Game Theory Analysis",
                payoff_matrix=payoff_matrix,
                player_a_strategies=player_a,
                player_b_strategies=player_b,
                has_saddle_point=saddle.get("has_saddle_point"),
                game_value=saddle.get("game_value"),
                saddle_point_strategy=saddle.get("maximin_strategy"),
                mixed_strategy=result.get("mixed_strategy_solution"),
                dominance_reduction=result.get("dominance_reduction")
            )
            db.add(gt_model)
            db.commit()
            save_audit_log(db, "GAME_THEORY", "game_theory", {
                "model_id": model_id,
                "has_saddle": saddle.get("has_saddle_point")
            })
            result["saved_model_id"] = model_id

        return result

    def analyze_network(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PERT/CPM and save to DB"""
        result = super().analyze_network(activities)

        with self.get_db() as db:
            model_id = generate_id("PERT")
            pert_model = ORPERTCPM(
                id=model_id,
                model_name="PERT/CPM Analysis",
                project_duration=result.get("project_duration"),
                critical_path=result.get("critical_path"),
                critical_path_duration=result.get("critical_path_duration"),
                total_variance=result.get("total_variance"),
                activities=result.get("activities")
            )
            db.add(pert_model)
            db.commit()
            save_audit_log(db, "PERT_CPM", "pert_cpm", {
                "model_id": model_id,
                "project_duration": result.get("project_duration"),
                "critical_path": result.get("critical_path")
            })
            result["saved_model_id"] = model_id

        return result

    def solve_knapsack(self, capacity: float, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Solve knapsack and save to DB"""
        result = super().solve_knapsack(capacity, items)

        with self.get_db() as db:
            model_id = generate_id("DP")
            ks_model = ORKnapsack(
                id=model_id,
                model_name="0/1 Knapsack",
                capacity=capacity,
                max_value=result.get("max_value"),
                selected_items=result.get("selected_items"),
                total_weight=result.get("total_weight"),
                items_count=len(items)
            )
            db.add(ks_model)
            db.commit()
            save_audit_log(db, "DYNAMIC_PROGRAMMING", "knapsack", {
                "model_id": model_id,
                "max_value": result.get("max_value")
            })
            result["saved_model_id"] = model_id

        return result

    def solve_goal_programming(self, goals: List[Dict], 
                               constraints: List[Dict], 
                               variables: List[str], 
                               method: str = "preemptive") -> Dict[str, Any]:
        """Solve goal programming and save to DB"""
        result = super().solve_goal_programming(goals, constraints, variables, method)

        with self.get_db() as db:
            model_id = generate_id("GP")
            gp_model = ORGoalProgramming(
                id=model_id,
                model_name="Goal Programming",
                method=method,
                priorities=result.get("priorities"),
                goals_achieved=result.get("goals_achieved")
            )
            db.add(gp_model)
            db.commit()
            save_audit_log(db, "GOAL_PROGRAMMING", "goal_programming", {
                "model_id": model_id,
                "method": method
            })
            result["saved_model_id"] = model_id

        return result

    def analyze_cost_profit(self, fixed_costs: float, variable_cost: float,
                           selling_price: float, target_profit: float = 0,
                           scenarios: List[Dict] = None) -> Dict[str, Any]:
        """CVP analysis and save to DB"""
        result = super().analyze_cost_profit(fixed_costs, variable_cost, selling_price, target_profit, scenarios)

        with self.get_db() as db:
            model_id = generate_id("CVP")
            basic = result.get("basic_analysis", {})
            cvp_model = ORCVPModel(
                id=model_id,
                model_name="CVP Analysis",
                fixed_costs=fixed_costs,
                variable_cost_per_unit=variable_cost,
                selling_price_per_unit=selling_price,
                target_profit=target_profit,
                break_even_units=basic.get("break_even_units"),
                break_even_revenue=basic.get("break_even_revenue"),
                contribution_margin=basic.get("contribution_margin_per_unit"),
                cm_ratio=basic.get("contribution_margin_ratio"),
                scenarios=result.get("scenarios")
            )
            db.add(cvp_model)
            db.commit()
            save_audit_log(db, "CVP_ANALYSIS", "cvp", {
                "model_id": model_id,
                "break_even": basic.get("break_even_units")
            })
            result["saved_model_id"] = model_id

        return result

    # =================================================================
    # QUERY METHODS
    # =================================================================

    def get_decision_history(self, limit: int = 50) -> List[Dict]:
        """Get recent decision analysis history"""
        with self.get_db() as db:
            models = db.query(ORDecisionModel).order_by(ORDecisionModel.created_at.desc()).limit(limit).all()
            return [{
                "id": m.id,
                "name": m.model_name,
                "criterion": m.criterion_used,
                "recommended": m.recommended_alternative,
                "value": m.recommended_value,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in models]

    def get_lp_history(self, limit: int = 50) -> List[Dict]:
        """Get recent LP solve history"""
        with self.get_db() as db:
            models = db.query(ORLPModel).order_by(ORLPModel.created_at.desc()).limit(limit).all()
            return [{
                "id": m.id,
                "name": m.model_name,
                "status": m.solve_status,
                "objective_value": m.objective_value,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in models]

    def get_audit_trail_db(self, limit: int = 100) -> List[Dict]:
        """Get audit trail from database (Sergey Protocol)"""
        with self.get_db() as db:
            audits = db.query(ORAuditTrail).order_by(ORAuditTrail.timestamp.desc()).limit(limit).all()
            return [{
                "id": a.id,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "operation": a.operation,
                "model_type": a.model_type,
                "details": a.details
            } for a in audits]

    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db_manager.get_table_stats()

    def export_all_models(self) -> Dict[str, Any]:
        """Export all saved models"""
        with self.get_db() as db:
            return {
                "decision_models": db.query(ORDecisionModel).count(),
                "lp_models": db.query(ORLPModel).count(),
                "game_theory": db.query(ORGameTheory).count(),
                "pert_cpm": db.query(ORPERTCPM).count(),
                "knapsack": db.query(ORKnapsack).count(),
                "goal_programming": db.query(ORGoalProgramming).count(),
                "cvp": db.query(ORCVPModel).count(),
                "audit_entries": db.query(ORAuditTrail).count(),
                "timestamp": datetime.now().isoformat()
            }
