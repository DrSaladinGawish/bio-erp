import logging, sys, os
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

import uvicorn
from app.main import app

if "--reload" in sys.argv:
    print("ERROR: --reload is unsafe from this launcher (wrong watch dir). Remove it.", file=sys.stderr)
    sys.exit(1)
logging.basicConfig(level=logging.WARNING)
uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info")
