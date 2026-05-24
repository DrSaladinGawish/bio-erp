from datetime import datetime
from sqlalchemy import Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class Currency(Base, BaseMixin):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(
        String(3), unique=True, nullable=False, comment="EGP, USD, EUR, AED, ..."
    )
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mid_rate: Mapped[float] = mapped_column(
        Float, default=1.0, comment="Mid-market rate to base currency"
    )
    buy_rate: Mapped[float] = mapped_column(
        Float, default=1.0, comment="Buy rate to base currency"
    )
    sell_rate: Mapped[float] = mapped_column(
        Float, default=1.0, comment="Sell rate to base currency"
    )
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2)


class CurrencyRate(Base, BaseMixin):
    __tablename__ = "currency_rates"

    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    rate_to_egp: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="CBE")

    currency = relationship("Currency")


class TransactionType(Base, BaseMixin):
    __tablename__ = "transaction_types"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=True)
    sign_effect: Mapped[int] = mapped_column(
        Integer, comment="+1=Debit, -1=Credit, 0=None"
    )
