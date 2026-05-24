from sqlalchemy import Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BilingualMixin


class PaymentTerm(Base, BaseMixin):
    __tablename__ = "payment_terms"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    days: Mapped[int] = mapped_column(Integer, default=0)
    discount_days: Mapped[int] = mapped_column(Integer, default=0)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class BankAccount(Base, BaseMixin):
    __tablename__ = "bank_accounts"

    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str] = mapped_column(String(100), nullable=True)
    swift_code: Mapped[str] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    coa_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)

    coa_account = relationship("COAAccount")


class BudgetCategory(Base, BaseMixin, BilingualMixin):
    __tablename__ = "budget_categories"

    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budget_categories.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    default_coa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )

    parent = relationship("BudgetCategory", remote_side="BudgetCategory.id")
    coa_account = relationship("COAAccount")


class TaxCode(Base, BaseMixin):
    __tablename__ = "tax_codes"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    tax_type: Mapped[str] = mapped_column(
        String(20), nullable=True, comment="VAT/GST/Sales"
    )
    coa_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )

    coa_account = relationship("COAAccount")
