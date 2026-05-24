from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BilingualMixin


class COACategory(Base, BaseMixin, BilingualMixin):
    __tablename__ = "coa_categories"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Balance Sheet / Income Statement"
    )
    accounts = relationship("COAAccount", back_populates="category")


class COAAccount(Base, BaseMixin, BilingualMixin):
    __tablename__ = "coa_accounts"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_categories.id"), nullable=False
    )
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Asset/Liability/Equity/Income/Expense"
    )
    is_control_account: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    opening_balance: Mapped[float] = mapped_column(default=0.0)
    opening_balance_date: Mapped[str] = mapped_column(String(10), nullable=True)

    category = relationship("COACategory", back_populates="accounts")
    children = relationship("COAAccount", backref="parent", remote_side="COAAccount.id")
