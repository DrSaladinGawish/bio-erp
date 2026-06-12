"""Test imports step by step to find blocker"""

import time, sys, os

sys.path.insert(0, "D:\\ERP System\\BIO_ERP")
os.chdir("D:\\ERP System\\BIO_ERP")


def try_import(label, module_str):
    t = time.time()
    try:
        __import__(module_str, fromlist=[""])
        elapsed = time.time() - t
        print(f"  OK  {label:50s} {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - t
        print(f"  FAIL {label:50s} {elapsed:.1f}s — {str(e)[:80]}")
        return False


# Step by step
try_import("app.config", "app.config")
try_import("app.database", "app.database")
try_import("app.models", "app.models")
try_import("app.auth", "app.auth")
try_import(
    "app.organs.incentivehouse_organ.sub_app", "app.organs.incentivehouse_organ.sub_app"
)
try_import(
    "app.organs.incentivehouse_organ.routers.bnk_router",
    "app.organs.incentivehouse_organ.routers.bnk_router",
)
try_import(
    "app.organs.incentivehouse_organ.routers.sal_router",
    "app.organs.incentivehouse_organ.routers.sal_router",
)
try_import("app.main", "app.main")
