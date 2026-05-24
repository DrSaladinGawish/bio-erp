from sqlalchemy import Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class ItemCategory(Base, BaseMixin):
    __tablename__ = "item_categories"

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="VEN, AV, CAT, DEC, TRN, STF, MRK, MISC",
    )
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    default_markup: Mapped[float] = mapped_column(Float, default=0.12)

    sub_categories = relationship("ItemSubCategory", back_populates="category")


class ItemSubCategory(Base, BaseMixin):
    __tablename__ = "item_sub_categories"

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("item_categories.id"), nullable=False
    )
    classification: Mapped[str] = mapped_column(
        String(100), nullable=True, comment="For ETA/GS1 coding"
    )

    category = relationship("ItemCategory", back_populates="sub_categories")


class EventMasterNode(Base, BaseMixin):
    __tablename__ = "event_master_nodes"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    layer: Mapped[int] = mapped_column(
        Integer, comment="1=Root, 2=Category, 3=Activity Item"
    )
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_master_nodes.id"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("item_categories.id"), nullable=True
    )
    sub_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("item_sub_categories.id"), nullable=True
    )
    uom: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Unit of Measure"
    )
    default_lead_time: Mapped[int] = mapped_column(
        Integer, default=0, comment="In days"
    )
    dependency_weight: Mapped[float] = mapped_column(Float, default=1.0)
    default_cost: Mapped[float] = mapped_column(Float, default=0.0)
    classification_code: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="GS1/EGS code for ETA"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    children = relationship(
        "EventMasterNode", backref="parent", remote_side="EventMasterNode.id"
    )
    category = relationship("ItemCategory")
    sub_category = relationship("ItemSubCategory")
