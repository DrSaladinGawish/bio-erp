import asyncio, asyncpg

async def fix():
    conn = await asyncpg.connect(
        "postgresql://postgres:postgres123@localhost:5432/bio_erp"
    )
    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='audit_logs'"
    )
    existing = [c["column_name"] for c in cols]
    print("Existing columns:", existing)

    if "row_hash" not in existing:
        await conn.execute("ALTER TABLE audit_logs ADD COLUMN row_hash VARCHAR(64)")
        print("Added row_hash")
    if "previous_hash" not in existing:
        await conn.execute("ALTER TABLE audit_logs ADD COLUMN previous_hash VARCHAR(64)")
        print("Added previous_hash")
    if "chain_verified" not in existing:
        await conn.execute(
            "ALTER TABLE audit_logs ADD COLUMN chain_verified BOOLEAN DEFAULT FALSE"
        )
        print("Added chain_verified")

    cols2 = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='audit_logs'"
    )
    print("Final columns:", [c["column_name"] for c in cols2])
    await conn.close()

asyncio.run(fix())
print("Migration complete")
