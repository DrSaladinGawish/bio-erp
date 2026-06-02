"""Check PostgreSQL connectivity"""
import psycopg2

creds = [
    ("postgres", "postgres123"),
    ("postgres", "bio_erp_secret"),
    ("bio_erp", "bio_erp_secret"),
    ("postgres", "postgres"),
]

for user, password in creds:
    try:
        conn = psycopg2.connect(host="localhost", port=5432, user=user, password=password, dbname="postgres", connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        dbs = [r[0] for r in cur.fetchall()]
        print(f"OK: user={user} pass={password} dbs={dbs}")
        conn.close()
        break
    except Exception as e:
        print(f"NO: user={user} pass={password} -> {e}")
