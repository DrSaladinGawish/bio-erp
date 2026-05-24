from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin


class Owner(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "owners"

    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    cost_center: Mapped[str] = mapped_column(String(50), nullable=True)
    acc_key: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    ownership_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    account = relationship("COAAccount", foreign_keys=[acc_key])
