from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base, BaseMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )


class Permission(Base, BaseMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="e.g. coa.create, event.read"
    )
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False)

    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )


class User(Base, BaseMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_en: Mapped[str] = mapped_column(String(255), nullable=True)
    full_name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), default=1
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, backref="users")
    branch = relationship("Branch", back_populates="users")
