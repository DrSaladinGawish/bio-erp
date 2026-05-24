"""Seed database with Flask-compatible roles and permissions.

Run: python -m app.seed
Or called from app.main lifespan.
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

# Format: (code, name_en, module)
FLASK_PERMISSIONS: list[tuple[str, str, str]] = [
    # Manufacturing
    ("batch:read", "Read batch records", "manufacturing"),
    ("batch:write", "Create/update batches", "manufacturing"),
    ("batch:release", "Release batches to production", "manufacturing"),
    ("batch:complete", "Mark batches as complete", "manufacturing"),
    # Materials & Bio-costing
    ("material:read", "Read material master data", "materials"),
    ("material:write", "Create/update materials", "materials"),
    ("biocost:read", "Read bio-costing data", "costing"),
    ("biocost:write", "Create/update bio-costing", "costing"),
    # Company/Client
    ("company:read", "Read company/branch/client data", "company"),
    ("company:write", "Create/update companies", "company"),
    # Users
    ("user:read", "Read user profiles", "users"),
    ("user:write", "Create/update users", "users"),
    # Analytics
    ("analytics:read", "Read dashboards and reports", "analytics"),
    # FastAPI-specific (extended)
    ("accounting.read", "Read accounting data", "accounting"),
    ("accounting.post", "Post GL entries", "accounting"),
    ("admin.access", "Access admin panel", "admin"),
    ("approval.read", "View approval rules", "approval"),
    ("approval.approve", "Approve/reject requests", "approval"),
    ("approval.manage", "Manage approval workflows", "approval"),
    ("budget.read", "Read budgets", "budget"),
    ("budget.update", "Update budgets", "budget"),
    ("budget.approve", "Approve budgets", "budget"),
    ("budget.lock", "Lock budget versions", "budget"),
    ("costing.read", "Read cost analysis", "costing"),
    ("costing.create", "Run cost analysis", "costing"),
    ("costing.update", "Update cost data", "costing"),
    ("currency.sync", "Sync currency rates", "currency"),
    ("currency.update", "Update currency rates", "currency"),
    ("currency_edit", "Edit currency config", "currency"),
    ("dashboard.read", "View dashboards", "dashboard"),
    ("event.read", "Read events", "events"),
    ("event.update", "Update events", "events"),
    ("finance.create", "Create finance records", "finance"),
    ("finance.read", "Read finance data", "finance"),
    ("finance.update", "Update finance records", "finance"),
    ("finance.post", "Post finance transactions", "finance"),
    ("finance.approve", "Approve finance transactions", "finance"),
    ("invoice_create", "Create ETA invoices", "einvoice"),
    ("invoice_view", "View ETA invoices", "einvoice"),
    ("pettycash.create", "Create petty cash", "pettycash"),
    ("pettycash.read", "Read petty cash", "pettycash"),
    ("pettycash.approve", "Approve petty cash", "pettycash"),
    ("procurement.create", "Create procurement", "procurement"),
    ("procurement.read", "Read procurement", "procurement"),
    ("procurement.approve", "Approve procurement", "procurement"),
    ("report.read", "Read reports", "reports"),
    ("rfq.read", "Read RFQs", "rfq"),
    ("rfq.create", "Create RFQs", "rfq"),
    ("rfq.award", "Award RFQs", "rfq"),
    ("supplier.read", "Read suppliers", "suppliers"),
    ("supplier.create", "Create suppliers", "suppliers"),
    ("supplier.update", "Update suppliers", "suppliers"),
]

# Flask-compatible role definitions (using FastAPI permission codes)
ROLE_DEFINITIONS: dict[str, list[str]] = {
    "read_only": [
        "user:read", "company:read", "batch:read", "biocost:read",
        "material:read", "analytics:read",
        "accounting.read", "budget.read", "costing.read", "currency.sync",
        "dashboard.read", "event.read", "finance.read", "invoice_view",
        "pettycash.read", "procurement.read", "report.read", "rfq.read",
        "supplier.read",
    ],
    "operator": [
        "user:read", "company:read", "batch:read", "biocost:read",
        "material:read", "analytics:read", "batch:write", "material:write",
        "biocost:write",
        "accounting.read", "budget.read", "costing.read", "currency.sync",
        "dashboard.read", "event.read", "finance.read", "invoice_view",
        "pettycash.read", "procurement.read", "report.read", "rfq.read",
        "supplier.read",
        "accounting.post", "budget.update", "costing.create", "currency.update",
        "event.update", "finance.create", "finance.post", "invoice_create",
        "pettycash.create", "procurement.create", "rfq.create",
    ],
    "manager": [
        "user:read", "company:read", "batch:read", "biocost:read",
        "material:read", "analytics:read", "batch:write", "material:write",
        "biocost:write", "batch:release", "batch:complete", "company:write",
        "accounting.read", "budget.read", "costing.read", "currency.sync",
        "dashboard.read", "event.read", "finance.read", "invoice_view",
        "pettycash.read", "procurement.read", "report.read", "rfq.read",
        "supplier.read",
        "accounting.post", "budget.update", "costing.create", "currency.update",
        "event.update", "finance.create", "finance.post", "invoice_create",
        "pettycash.create", "procurement.create", "rfq.create",
        "budget.approve", "budget.lock", "costing.update", "finance.update",
        "finance.approve", "pettycash.approve", "procurement.approve",
        "rfq.award", "supplier.update",
    ],
    "admin": [
        "user:read", "company:read", "batch:read", "biocost:read",
        "material:read", "analytics:read", "batch:write", "material:write",
        "biocost:write", "batch:release", "batch:complete", "company:write",
        "user:write",
        "accounting.read", "budget.read", "costing.read", "currency.sync",
        "dashboard.read", "event.read", "finance.read", "invoice_view",
        "pettycash.read", "procurement.read", "report.read", "rfq.read",
        "supplier.read",
        "accounting.post", "budget.update", "costing.create", "currency.update",
        "event.update", "finance.create", "finance.post", "invoice_create",
        "pettycash.create", "procurement.create", "rfq.create",
        "budget.approve", "budget.lock", "costing.update", "finance.update",
        "finance.approve", "pettycash.approve", "procurement.approve",
        "rfq.award", "supplier.update",
        "admin.access", "approval.read", "approval.approve", "approval.manage",
        "currency_edit",
    ],
}


def get_all_permission_codes() -> list[str]:
    return [p[0] for p in FLASK_PERMISSIONS]


async def seed_permissions(db: AsyncSession) -> None:
    """Insert missing permissions into the database."""
    from app.models.auth import Permission

    for code, name_en, module in FLASK_PERMISSIONS:
        existing = await db.execute(select(Permission).where(Permission.code == code))
        if not existing.scalar_one_or_none():
            db.add(Permission(code=code, name_en=name_en, module=module))
    await db.commit()


async def seed_roles(db: AsyncSession) -> None:
    """Insert missing roles and assign their permissions."""
    from app.models.auth import Permission, Role, role_permissions

    for role_name, perm_codes in ROLE_DEFINITIONS.items():
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Flask-compatible {role_name} role")
            db.add(role)
            await db.flush()

        # Assign permissions
        for code in perm_codes:
            perm_result = await db.execute(
                select(Permission).where(Permission.code == code)
            )
            perm = perm_result.scalar_one_or_none()
            if perm:
                link_exists = await db.execute(
                    select(role_permissions).where(
                        role_permissions.c.role_id == role.id,
                        role_permissions.c.permission_id == perm.id,
                    )
                )
                if not link_exists.first():
                    await db.execute(
                        role_permissions.insert().values(
                            role_id=role.id, permission_id=perm.id
                        )
                    )
    await db.commit()


async def seed_all(db: AsyncSession) -> None:
    """Run all seed operations."""
    await seed_permissions(db)
    await seed_roles(db)
