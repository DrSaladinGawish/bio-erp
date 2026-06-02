"""Test module loading to debug v2 router issue"""
import sys, json

# Clear any cached modules
for mod_name in list(sys.modules.keys()):
    if "incentivehouse" in mod_name or "erp_builder" in mod_name:
        del sys.modules[mod_name]

sys.path.insert(0, "D:\\ERP System\\BIO_ERP\\app\\organs\\incentivehouse_organ")

# First import the v2 module directly
from erp_builder_v2 import v2_router
print(f"[DIRECT IMPORT] v2_router: {v2_router}")
print(f"[DIRECT IMPORT] v2_router routes: {len(v2_router.routes)}")
for r in v2_router.routes[:3]:
    print(f"  {r.methods} {r.path}")

# Now import server
import importlib.util
spec = importlib.util.spec_from_file_location(
    "incentivehouse_server",
    "D:\\ERP System\\BIO_ERP\\app\\organs\\incentivehouse_organ\\incentivehouse_server.py"
)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    print("App loaded OK")
    
    # Check attributes
    print(f"Has 'v2_router': {hasattr(mod, 'v2_router')}")
    print(f"Has '_v2_pipeline': {hasattr(mod, '_v2_pipeline')}")
    
    # List ALL routes
    all_paths = list(mod.app.openapi()["paths"].keys())
    v2_paths = [p for p in all_paths if "/v2" in p]
    print(f"Total paths: {len(all_paths)}")
    print(f"V2 paths: {len(v2_paths)}")
    for p in v2_paths:
        print(f"  {p}")
    
    # Also check the incentivehouse_app routes directly
    print(f"incentivehouse_app.routes: {len(mod.incentivehouse_app.routes)}")
    for r in mod.incentivehouse_app.routes:
        path = getattr(r, 'path', str(r))
        print(f"  {path}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
