from datetime import date
from sqlalchemy import Integer, String, Float, ForeignKey, Text, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class TargetCosting(Base, BaseMixin):
    __tablename__ = "target_costing"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    target_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)
    target_cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_cost: Mapped[float] = mapped_column(Float, default=0.0)
    cost_gap: Mapped[float] = mapped_column(Float, default=0.0)
    gap_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class LifeCycleCost(Base, BaseMixin):
    __tablename__ = "lifecycle_costs"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    planned_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    variance: Mapped[float] = mapped_column(Float, default=0.0)
    cost_driver: Mapped[str] = mapped_column(String(100), nullable=True)
    driver_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)

    event = relationship("Event")


class ActivityCostPool(Base, BaseMixin):
    __tablename__ = "activity_cost_pools"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    pool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_driver: Mapped[str] = mapped_column(String(100), nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    driver_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    cost_driver_rate: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class ValueChainActivity(Base, BaseMixin):
    __tablename__ = "value_chain_activities"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    activity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_attributable: Mapped[float] = mapped_column(Float, default=0.0)
    value_added: Mapped[float] = mapped_column(Float, default=0.0)
    value_added_pct: Mapped[float] = mapped_column(Float, default=0.0)
    benchmark_cost: Mapped[float] = mapped_column(Float, nullable=True)
    benchmark_gap: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class KaizenCosting(Base, BaseMixin):
    __tablename__ = "kaizen_costing"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    kaizen_number: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    baseline_cost: Mapped[float] = mapped_column(Float, nullable=False)
    target_reduction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    target_cost: Mapped[float] = mapped_column(Float, nullable=False)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0)
    achieved_reduction_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    responsible_person: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class CostVarianceAnalysis(Base, BaseMixin):
    __tablename__ = "cost_variance_analysis"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    line_item: Mapped[str] = mapped_column(String(255), nullable=False)
    standard_cost: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0)
    standard_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    actual_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    standard_price: Mapped[float] = mapped_column(Float, default=0.0)
    actual_price: Mapped[float] = mapped_column(Float, default=0.0)
    price_variance: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_variance: Mapped[float] = mapped_column(Float, default=0.0)
    total_variance: Mapped[float] = mapped_column(Float, default=0.0)
    is_favorable: Mapped[bool] = mapped_column(Boolean, default=True)
    root_cause: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class BalancedScorecard(Base, BaseMixin):
    __tablename__ = "balanced_scorecards"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    financial_score: Mapped[float] = mapped_column(Float, default=0.0)
    customer_score: Mapped[float] = mapped_column(Float, default=0.0)
    internal_process_score: Mapped[float] = mapped_column(Float, default=0.0)
    learning_growth_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    event = relationship("Event")
    objectives = relationship("BSCObjective", back_populates="bsc")
    indicators = relationship("BSCIndicator", back_populates="bsc")


class BSCObjective(Base, BaseMixin):
    __tablename__ = "bsc_objectives"

    bsc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("balanced_scorecards.id"), nullable=False
    )
    perspective: Mapped[str] = mapped_column(String(30), nullable=False)
    objective_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)

    bsc = relationship("BalancedScorecard", back_populates="objectives")
    indicators = relationship("BSCIndicator", back_populates="objective")


class BSCIndicator(Base, BaseMixin):
    __tablename__ = "bsc_indicators"

    bsc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("balanced_scorecards.id"), nullable=False
    )
    objective_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bsc_objectives.id"), nullable=True
    )
    perspective: Mapped[str] = mapped_column(String(30), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    formula: Mapped[str] = mapped_column(String(255), nullable=True)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")

    bsc = relationship("BalancedScorecard", back_populates="indicators")
    objective = relationship("BSCObjective", back_populates="indicators")
    measurements = relationship("BSCMeasurement", back_populates="indicator")


class BSCMeasurement(Base, BaseMixin):
    __tablename__ = "bsc_measurements"

    indicator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bsc_indicators.id"), nullable=False
    )
    measurement_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    indicator = relationship("BSCIndicator", back_populates="measurements")


class EventProfitability(Base, BaseMixin):
    __tablename__ = "event_profitability"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False, unique=True
    )
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    direct_costs: Mapped[float] = mapped_column(Float, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    gross_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    operating_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    roi: Mapped[float] = mapped_column(Float, default=0.0)
    break_even_attendees: Mapped[float] = mapped_column(Float, default=0.0)
    actual_attendees: Mapped[float] = mapped_column(Float, nullable=True)
    revenue_per_attendee: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_attendee: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_margin: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_ratio: Mapped[float] = mapped_column(Float, default=0.0)

    event = relationship("Event")
