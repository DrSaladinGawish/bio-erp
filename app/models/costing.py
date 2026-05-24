from datetime import timezone, datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Enum as SAEnum,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin
import enum


class CostType(str, enum.Enum):
    DIRECT_MATERIAL = "direct_material"
    DIRECT_LABOR = "direct_labor"
    MANUFACTURING_OVERHEAD = "manufacturing_overhead"
    SELLING = "selling"
    ADMINISTRATIVE = "administrative"
    FINANCIAL = "financial"


class CostCenterType(str, enum.Enum):
    PRODUCTION = "production"
    SERVICE = "service"
    ADMIN = "admin"
    SALES = "sales"


class CostCenter(Base, BaseMixin):
    __tablename__ = "cost_centers"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=True)
    type: Mapped[CostCenterType] = mapped_column(
        SAEnum(CostCenterType), default=CostCenterType.PRODUCTION
    )
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=True
    )
    manager_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    budget_limit: Mapped[float] = mapped_column(Float, default=0.0)

    parent = relationship(
        "CostCenter", back_populates="children", remote_side="CostCenter.id"
    )
    children = relationship(
        "CostCenter", back_populates="parent", foreign_keys="CostCenter.parent_id"
    )
    allocations = relationship("CostAllocation", back_populates="cost_center")
    activities = relationship("ActivityCost", back_populates="cost_center")


class CostAllocation(Base, BaseMixin):
    __tablename__ = "cost_allocations"

    cost_center_id: Mapped[int] = mapped_column(Integer, ForeignKey("cost_centers.id"))
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    cost_type: Mapped[CostType] = mapped_column(SAEnum(CostType), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    allocation_base: Mapped[str] = mapped_column(String(50), nullable=True)
    base_quantity: Mapped[float] = mapped_column(Float, default=1.0)
    rate_per_unit: Mapped[float] = mapped_column(Float, nullable=True)
    is_actual: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    cost_center = relationship("CostCenter", back_populates="allocations")


class ActivityCost(Base, BaseMixin):
    __tablename__ = "activity_costs"

    cost_center_id: Mapped[int] = mapped_column(Integer, ForeignKey("cost_centers.id"))
    activity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_driver: Mapped[str] = mapped_column(String(50), nullable=False)
    driver_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_driver: Mapped[float] = mapped_column(Float, nullable=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)

    cost_center = relationship("CostCenter", back_populates="activities")


class StandardCost(Base, BaseMixin):
    __tablename__ = "standard_costs"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_master_nodes.id"), nullable=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)

    material_std: Mapped[float] = mapped_column(Float, default=0.0)
    labor_std: Mapped[float] = mapped_column(Float, default=0.0)
    overhead_std: Mapped[float] = mapped_column(Float, default=0.0)

    material_actual: Mapped[float] = mapped_column(Float, default=0.0)
    labor_actual: Mapped[float] = mapped_column(Float, default=0.0)
    overhead_actual: Mapped[float] = mapped_column(Float, default=0.0)

    material_variance: Mapped[float] = mapped_column(Float, default=0.0)
    labor_variance: Mapped[float] = mapped_column(Float, default=0.0)
    overhead_variance: Mapped[float] = mapped_column(Float, default=0.0)

    quantity_std: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_actual: Mapped[float] = mapped_column(Float, default=0.0)
    efficiency_variance: Mapped[float] = mapped_column(Float, default=0.0)


class EventCostAnalysis(Base, BaseMixin):
    __tablename__ = "event_cost_analyses"

    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))

    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)

    direct_materials: Mapped[float] = mapped_column(Float, default=0.0)
    direct_labor: Mapped[float] = mapped_column(Float, default=0.0)
    subcontractor_costs: Mapped[float] = mapped_column(Float, default=0.0)

    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    gross_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    venue_rental: Mapped[float] = mapped_column(Float, default=0.0)
    equipment_rental: Mapped[float] = mapped_column(Float, default=0.0)
    transportation: Mapped[float] = mapped_column(Float, default=0.0)
    catering: Mapped[float] = mapped_column(Float, default=0.0)
    marketing: Mapped[float] = mapped_column(Float, default=0.0)
    staff_costs: Mapped[float] = mapped_column(Float, default=0.0)
    other_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    total_operating_expenses: Mapped[float] = mapped_column(Float, default=0.0)

    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    breakeven_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    organ_efficiency: Mapped[float] = mapped_column(Float, default=0.0)
    cell_utilization: Mapped[float] = mapped_column(Float, default=0.0)
    neural_load: Mapped[float] = mapped_column(Float, default=0.0)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    event = relationship("Event")


class BudgetPeriod(Base, BaseMixin):
    __tablename__ = "budget_periods"

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=True)
    month: Mapped[int] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("fiscal_year", "quarter", "month", name="uq_budget_period"),
    )


class BudgetLine(Base, BaseMixin):
    __tablename__ = "budget_lines"

    cost_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=False
    )
    coa_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    budget_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budget_periods.id"), nullable=False
    )
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False, default=1
    )
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    cost_center = relationship("CostCenter")
    coa_account = relationship("COAAccount")
    budget_period = relationship("BudgetPeriod")

    __table_args__ = (
        UniqueConstraint(
            "cost_center_id",
            "coa_account_id",
            "budget_period_id",
            "branch_id",
            name="uq_budget_line",
        ),
    )

    @property
    def variance_amount(self) -> Decimal:
        return self.actual_amount - self.budgeted_amount

    @property
    def variance_percent(self) -> float:
        if self.budgeted_amount == 0:
            return 0.0
        return float(
            (self.actual_amount - self.budgeted_amount) / self.budgeted_amount * 100
        )


class CrossCenterAllocation(Base, BaseMixin):
    __tablename__ = "cross_center_allocations"

    from_cost_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=False
    )
    to_cost_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=False
    )
    budget_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budget_periods.id"), nullable=False
    )
    allocation_base: Mapped[str] = mapped_column(String(50), nullable=False)
    rate_percent: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    is_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    from_cost_center = relationship("CostCenter", foreign_keys=[from_cost_center_id])
    to_cost_center = relationship("CostCenter", foreign_keys=[to_cost_center_id])
    budget_period = relationship("BudgetPeriod")
