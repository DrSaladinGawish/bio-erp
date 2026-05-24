from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, declarative_mixin


def _utcnow() -> datetime:
    """Timezone-naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@declarative_mixin
class BaseMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


@declarative_mixin
class BilingualMixin:
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)


@declarative_mixin
class BranchAwareMixin:
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=False, default=1
    )


@declarative_mixin
class CurrencyAwareMixin:
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    conversion_rate: Mapped[float] = mapped_column(Float, default=1.0)
    amount_egp: Mapped[float] = mapped_column(Float, nullable=True)


@declarative_mixin
class AuditableMixin:
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
