import sqlite3
import os

db_path = r'D:\EventCore_ERP\backend\eventcore.db'
if not os.path.exists(db_path):
    print(f"File not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

tables = ['vendors', 'chart_accounts', 'journal_vouchers', 'sales_invoices', 'clients']
for table in tables:
    try:
        count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")
    except Exception as e:
        print(f"{table}: Error - {e}")

try:
    active_vendors = c.execute("SELECT COUNT(*) FROM vendors WHERE status='active'").fetchone()[0]
    print(f"Active Vendors: {active_vendors}")
except: pass

try:
    active_gl = c.execute("SELECT COUNT(*) FROM chart_accounts WHERE is_active=1").fetchone()[0]
    print(f"Active GL: {active_gl}")
except: pass

conn.close()
