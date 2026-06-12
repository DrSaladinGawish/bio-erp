"""
OR-ERP Database Models (SQLAlchemy)
====================================
PostgreSQL tables for persisting OR analysis results.
Compatible with: EventManager ERP v9.2 / BIO-ERP v5.1
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    JSON, ForeignKey, create_engine, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional
import uuid

Base = declarative_base()

# =============================================================================
# CORE TABLES
# =============================================================================

class ORDecisionModel(Base):
    """Chapter 2 & 9: Decision Analysis results"""
    __tablename__ = "or_decision_models"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    model_description = Column(Text)
    criterion_used = Column(String(50))
    alpha_value = Column(Float, default=0.50)
    states_count = Column(Integer, nullable=False)
    alternatives_count = Column(Integer, nullable=False)
    payoff_matrix = Column(JSON, nullable=False)
    probabilities = Column(JSON)
    recommended_alternative = Column(String(255))
    recommended_value = Column(Float)
    evpi = Column(Float)
    full_report = Column(JSON)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ORLPModel(Base):
    """Chapters 2, 4, 5: Linear Programming results"""
    __tablename__ = "or_lp_models"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    objective_function = Column(JSON, nullable=False)
    constraints = Column(JSON, nullable=False)
    variable_count = Column(Integer, nullable=False)
    constraint_count = Column(Integer, nullable=False)
    solution = Column(JSON)
    objective_value = Column(Float)
    shadow_prices = Column(JSON)
    sensitivity_report = Column(JSON)
    solve_status = Column(String(50))
    solver_message = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class ORInventoryItem(Base):
    """Chapter 5: Inventory master data"""
    __tablename__ = "or_inventory_items"

    id = Column(String(50), primary_key=True)
    sku = Column(String(100), unique=True, nullable=False)
    item_name = Column(String(255), nullable=False)
    category_id = Column(String(50))
    annual_demand = Column(Float, nullable=False)
    ordering_cost = Column(Float, nullable=False)
    holding_cost_per_unit = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=0)
    daily_demand = Column(Float)
    stockout_cost = Column(Float)
    production_rate = Column(Float)
    supplier_id = Column(String(50))
    abc_class = Column(String(1))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORInventoryPolicy(Base):
    """Chapter 5: Calculated inventory policies"""
    __tablename__ = "or_inventory_policies"

    id = Column(String(50), primary_key=True)
    item_id = Column(String(50), ForeignKey("or_inventory_items.id"), nullable=False)
    model_type = Column(String(50))
    optimal_order_quantity = Column(Float)
    max_inventory = Column(Float)
    max_shortage = Column(Float)
    reorder_point = Column(Float)
    safety_stock = Column(Float)
    total_annual_cost = Column(Float)
    purchase_cost = Column(Float)
    ordering_cost_annual = Column(Float)
    holding_cost_annual = Column(Float)
    cycle_time_days = Column(Float)
    orders_per_year = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class ORTransportPlan(Base):
    """Chapter 6: Transportation optimization results"""
    __tablename__ = "or_transport_plans"

    id = Column(String(50), primary_key=True)
    plan_name = Column(String(255), nullable=False)
    method = Column(String(50))
    total_cost = Column(Float)
    allocation_matrix = Column(JSON)
    is_optimized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORGameTheory(Base):
    """Chapter 7: Game Theory analysis"""
    __tablename__ = "or_game_theory"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    payoff_matrix = Column(JSON, nullable=False)
    player_a_strategies = Column(JSON)
    player_b_strategies = Column(JSON)
    has_saddle_point = Column(Boolean)
    game_value = Column(Float)
    saddle_point_strategy = Column(JSON)
    mixed_strategy = Column(JSON)
    dominance_reduction = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORPERTCPM(Base):
    """Chapter 8: PERT/CPM network analysis"""
    __tablename__ = "or_pert_cpm"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    project_duration = Column(Float)
    critical_path = Column(JSON)
    critical_path_duration = Column(Float)
    total_variance = Column(Float)
    activities = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORKnapsack(Base):
    """Chapters 9 & 11: Dynamic Programming results"""
    __tablename__ = "or_knapsack"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    capacity = Column(Float, nullable=False)
    max_value = Column(Integer)
    selected_items = Column(JSON)
    total_weight = Column(Float)
    items_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORGoalProgramming(Base):
    """Chapter 10: Goal Programming results"""
    __tablename__ = "or_goal_programming"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    method = Column(String(50))
    priorities = Column(JSON)
    goals_achieved = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORCVPModel(Base):
    """Chapter 4: Cost-Volume-Profit analysis"""
    __tablename__ = "or_cvp_models"

    id = Column(String(50), primary_key=True)
    model_name = Column(String(255), nullable=False)
    fixed_costs = Column(Float, nullable=False)
    variable_cost_per_unit = Column(Float, nullable=False)
    selling_price_per_unit = Column(Float, nullable=False)
    target_profit = Column(Float, default=0)
    break_even_units = Column(Float)
    break_even_revenue = Column(Float)
    contribution_margin = Column(Float)
    cm_ratio = Column(Float)
    scenarios = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ORAuditTrail(Base):
    """Sergey Protocol: Full audit trail"""
    __tablename__ = "or_audit_trail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    operation = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)
    model_id = Column(String(50))
    details = Column(JSON)
    user_id = Column(String(100))
    session_id = Column(String(100))
    ip_address = Column(String(45))
    execution_time_ms = Column(Integer)

# =============================================================================
# DATABASE MANAGER
# =============================================================================

class ORDatabaseManager:
    """Manages OR-ERP database operations"""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all OR tables"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all OR tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def check_connection(self) -> bool:
        """Verify database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def get_table_stats(self) -> dict:
        """Get row counts for all OR tables"""
        stats = {}
        inspector = inspect(self.engine)
        for table_name in inspector.get_table_names():
            if table_name.startswith("or_"):
                with self.engine.connect() as conn:
                    result = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    stats[table_name] = result.scalar()
        return stats

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_id(prefix: str = "OR") -> str:
    """Generate unique ID with prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"

def save_decision_analysis(db: Session, result: dict, user_id: str = None) -> str:
    """Save decision analysis result to database"""
    model_id = generate_id("DEC")
    db_model = ORDecisionModel(
        id=model_id,
        model_name=result.get("model_name", "Decision Analysis"),
        criterion_used=result.get("criterion"),
        states_count=len(result.get("full_report", {}).get("payoff_matrix", {})),
        alternatives_count=len(result.get("full_report", {}).get("maximax", [])),
        payoff_matrix=result.get("full_report", {}).get("payoff_matrix"),
        recommended_alternative=result.get("recommended_alternative"),
        recommended_value=result.get("value"),
        evpi=result.get("full_report", {}).get("evpi"),
        full_report=result.get("full_report"),
        created_by=user_id
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return model_id

def save_lp_result(db: Session, result: dict, model_name: str, user_id: str = None) -> str:
    """Save LP result to database"""
    model_id = generate_id("LP")
    db_model = ORLPModel(
        id=model_id,
        model_name=model_name,
        objective_function=result.get("objective"),
        constraints=result.get("constraints"),
        variable_count=len(result.get("solution", [])),
        constraint_count=len(result.get("shadow_prices", [])),
        solution=result.get("solution"),
        objective_value=result.get("objective_value"),
        shadow_prices=result.get("shadow_prices"),
        solve_status="success" if result.get("success") else "failed",
        solver_message=result.get("message"),
        created_by=user_id
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return model_id

def save_audit_log(db: Session, operation: str, model_type: str, details: dict, 
                   user_id: str = None, session_id: str = None) -> int:
    """Save audit trail entry (Sergey Protocol)"""
    audit = ORAuditTrail(
        operation=operation,
        model_type=model_type,
        details=details,
        user_id=user_id,
        session_id=session_id
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit.id

# =============================================================================
# ALEMBIC MIGRATION SCRIPT (for existing projects)
# =============================================================================

"""
# Run these commands to create migration:
# alembic revision --autogenerate -m "Add OR-ERP tables"
# alembic upgrade head

# Or use the SQL schema directly:
# psql -d your_db -f or_erp_schema.sql
"""
