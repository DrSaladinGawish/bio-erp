"""
Seed demo clients + AR customers so the churn ANN can be trained.

Usage:
    python scripts/seed_demo_clients.py            # seed if empty
    python scripts/seed_demo_clients.py --purge    # delete demo rows only

All rows are tagged notes='DEMO seed data' for easy identification.
"""

import argparse
import asyncio
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.client import Client
from app.organs.far_ar_organ.models import ARCustomer

DEMO_TAG = "DEMO seed data"
N_CLIENTS = 60


def get_engine():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp",
    )
    return create_async_engine(url)


async def purge(db: AsyncSession) -> None:
    res1 = await db.execute(delete(ARCustomer).where(ARCustomer.notes == DEMO_TAG))
    res2 = await db.execute(delete(Client).where(Client.notes == DEMO_TAG))
    await db.commit()
    print(f"purged: ar_customers={res1.rowcount}, clients={res2.rowcount}")


async def seed(db: AsyncSession) -> None:
    existing = await db.execute(
        select(func.count()).select_from(Client).where(Client.notes == DEMO_TAG)
    )
    if (existing.scalar() or 0) > 0:
        print("demo clients already present — nothing to do")
        return

    rng = random.Random(42)
    clients = []
    ar_rows = []

    for i in range(1, N_CLIENTS + 1):
        code = f"CL{i:04d}"
        credit_limit = round(rng.uniform(10_000, 500_000), 2)
        # ~35% of clients run near/over their credit usage -> churn label True
        if rng.random() < 0.35:
            balance = round(credit_limit * rng.uniform(0.7, 1.1), 2)
        else:
            balance = round(credit_limit * rng.uniform(0.05, 0.5), 2)

        clients.append(
            Client(
                code=code,
                name_en=f"Demo Client {i:02d}",
                name_ar=f"عميل تجريبي {i:02d}",
                email=f"demo{i:02d}@example.com",
                phone1=f"+20100{i:06d}",
                credit_limit=credit_limit,
                balance=balance,
                notes=DEMO_TAG,
            )
        )

        if rng.random() < 0.8:
            credit_used = round(balance * rng.uniform(0.3, 1.05), 2)
            ar_rows.append(
                ARCustomer(
                    code=code,
                    name_en=f"AR Demo Customer {i:02d}",
                    credit_limit=credit_limit,
                    credit_used=max(credit_used, 0),
                    payment_terms=rng.choice([15, 30, 45, 60, 90]),
                    discount_pct=rng.choice([0, 0, 1.5, 2.5, 5]),
                    risk_rating=rng.choice(["A", "B", "B", "C"]),
                    notes=DEMO_TAG,
                )
            )

    db.add_all(clients)
    db.add_all(ar_rows)
    await db.commit()
    print(f"seeded: {len(clients)} clients, {len(ar_rows)} ar_customers")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--purge", action="store_true")
    args = parser.parse_args()

    engine = get_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        if args.purge:
            await purge(db)
        else:
            await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
