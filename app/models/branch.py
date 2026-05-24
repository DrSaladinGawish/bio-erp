from sqlalchemy import Integer, String, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BilingualMixin


class Branch(Base, BaseMixin, BilingualMixin):
    __tablename__ = "branches"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    address_en: Mapped[str] = mapped_column(String(500), nullable=True)
    address_ar: Mapped[str] = mapped_column(String(500), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    tax_authority: Mapped[str] = mapped_column(
        String(100), nullable=True, comment="ETA / FTA"
    )
    vat_rate: Mapped[float] = mapped_column(
        Float, default=0.14, comment="14% EG, 5% UAE"
    )
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Egypt")
    currency_id: Mapped[int] = mapped_column(
        Integer, default=1, comment="Default currency for this branch"
    )
    is_hq: Mapped[bool] = mapped_column(Boolean, default=False)

    users = relationship("User", back_populates="branch")
