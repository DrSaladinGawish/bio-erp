from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BilingualMixin, BranchAwareMixin


class Client(Base, BaseMixin, BilingualMixin, BranchAwareMixin):
    __tablename__ = "clients"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    tax_id: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Egyptian Tax ID"
    )
    commercial_registration: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone1: Mapped[str] = mapped_column(String(50), nullable=True)
    phone2: Mapped[str] = mapped_column(String(50), nullable=True)
    address_en: Mapped[str] = mapped_column(String(500), nullable=True)
    address_ar: Mapped[str] = mapped_column(String(500), nullable=True)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    acc_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("coa_accounts.id"),
        nullable=True,
        comment="Linked COA account",
    )
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)

    account = relationship("COAAccount", foreign_keys=[acc_key])
