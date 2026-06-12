#!/usr/bin/env python3
"""
ERP IH Launcher Dashboard — Part 4 P1
Neural Graph Theme + Module Launcher Grid + Document Manager
Port: 9003 (standalone) or mounted at /api/v1/launcher/ (merged)
"""

import os
import sys
import time
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

# FastAPI imports
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Third-party
import uvicorn

# ═════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "bio_erp"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "connect_timeout": 5,
}

HERE = Path(__file__).parent.resolve()
DASHBOARD_HTML_PATH = HERE / "dashboard_part4_p1.html"

# Fallback paths
if not DASHBOARD_HTML_PATH.exists():
    DASHBOARD_HTML_PATH = HERE.parent.parent.parent / "dashboard_part4_p1.html"

# Known ERP data files to scan
KNOWN_FILES = [
    Path("D:/Data_Base_Mtbls.xlsx"),
    Path("D:/Bnk_TRNX SOURCE.xlsx"),
    Path("D:/Bnk_Trnx_Sub_Key.xlsx"),
    Path("D:/Bnk_TRNX.xlsx"),
]

STAGING_DIR = Path("D:/IncentiveHouse_ERP/staging")

# Module configuration
MODULES_CONFIG = [
    {
        "id": "bio_erp",
        "name": "Bio-ERP Core",
        "emoji": "🧠",
        "role": "Brain",
        "port": 8000,
        "url": "http://localhost:8000",
        "api_docs": "http://localhost:8000/docs",
    },
    {
        "id": "ih_erp",
        "name": "IncentiveHouse",
        "emoji": "🏠",
        "role": "Organ",
        "port": 9001,
        "url": "http://localhost:9001",
        "api_docs": "http://localhost:9001/docs",
    },
    {
        "id": "eventcore",
        "name": "EventCore",
        "emoji": "📊",
        "role": "Organ",
        "port": 8001,
        "url": "http://localhost:8001",
        "api_docs": "http://localhost:8001/docs",
    },
    {
        "id": "or_erp",
        "name": "OR-ERP",
        "emoji": "⚙️",
        "role": "Organ",
        "port": 8000,
        "url": "http://localhost:8000/api/v1/or/docs",
        "api_docs": "http://localhost:8000/api/v1/or/docs",
    },
    {
        "id": "scm",
        "name": "SCM Module",
        "emoji": "💰",
        "role": "Organ",
        "port": None,
        "url": None,
        "api_docs": None,
    },
    {
        "id": "launcher",
        "name": "Launcher P4",
        "emoji": "🌊",
        "role": "Cortex",
        "port": 9003,
        "url": "http://localhost:9003",
        "api_docs": "http://localhost:9003/docs",
    },
    {
        "id": "aals",
        "name": "AALS Library",
        "emoji": "📚",
        "role": "Cell",
        "port": 5000,
        "url": "http://localhost:5000",
        "api_docs": None,
    },
]

# ═════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class DataFlowNode:
    id: str
    label: str
    type: str
    status: str
    description: str = ""
    group: str = ""

@dataclass
class DataFlowEdge:
    from_node: str
    to_node: str
    status: str
    label: str = ""
    description: str = ""

@dataclass
class DataLocation:
    entity_name: str
    primary_module: str
    entity_type: str
    location: str
    health_status: str
    record_count: Optional[int] = None
    last_update: Optional[str] = None

@dataclass
class MasterTableHealth:
    table_name: str
    module: str
    row_count: int
    duplicate_count: int
    null_count: int
    health_score: int
    recommendation: str
    last_scan: str

@dataclass
class DataFlowSnapshot:
    timestamp: str
    overall_flow_health: int
    overall_data_health: int
    overall_master_health: int
    critical_alerts: List[Dict]
    nodes: List[Dict]
    edges: List[Dict]
    master_tables: List[Dict]
    data_locations: List[Dict]

@dataclass
class ModuleStatus:
    id: str
    name: str
    emoji: str
    role: str
    status: str
    health: int
    port: Optional[int]
    url: Optional[str]
    api_docs: Optional[str]
    last_seen: Optional[str]

@dataclass
class DocumentFile:
    name: str
    path: str
    size_mb: float
    last_modified: Optional[str]
    staleness_hours: float
    status: str
    records: Optional[int]
    sheets: Optional[int]

# ═════════════════════════════════════════════════════════════════════════════
#  FLOW TOPOLOGY — Neural Anatomy (Brain / Organs / Cells)
# ═════════════════════════════════════════════════════════════════════════════

FLOW_TOPOLOGY = [
    # BRAIN (Level 0)
    DataFlowNode("brain", "Bio-ERP Core", "brain", "online", "Central nervous system of the ERP", "core"),

    # ORGANS (Level 1)
    DataFlowNode("ih_organ", "IncentiveHouse", "module", "online", "Sales, events, bank reconciliation", "organ"),
    DataFlowNode("ec_organ", "EventCore", "module", "online", "Event management and coordination", "organ"),
    DataFlowNode("or_organ", "OR-ERP", "module", "online", "Operations research analytics", "organ"),
    DataFlowNode("scm_organ", "SCM Module", "module", "offline", "Supply chain management", "organ"),
    DataFlowNode("aals_organ", "AALS Library", "module", "online", "Academic document management", "organ"),

    # DATABASE TABLES (Level 1-2)
    DataFlowNode("db_clients", "Clients", "database_table", "online", "Master client records", "cell"),
    DataFlowNode("db_vendors", "Vendors", "database_table", "online", "Master vendor records", "cell"),
    DataFlowNode("db_events", "Events", "database_table", "online", "Event master data", "cell"),
    DataFlowNode("db_bnk", "Bank Transactions", "database_table", "stale", "Bank reconciliation data", "cell"),
    DataFlowNode("db_coa", "Chart of Accounts", "database_table", "online", "GL account master", "cell"),
    DataFlowNode("db_staff", "Staff", "database_table", "online", "Employee master data", "cell"),

    # FILES (Level 2)
    DataFlowNode("file_mtbls", "Data_Base_Mtbls.xlsx", "file", "online", "Master data Excel (13 sheets, 1751 rows)", "cell"),
    DataFlowNode("file_bnk", "Bnk_TRNX SOURCE.xlsx", "file", "stale", "Bank transactions Excel (2501 rows)", "cell"),
    DataFlowNode("file_subkey", "Bnk_Trnx_Sub_Key.xlsx", "file", "online", "Transaction sub-key mapping", "cell"),

    # APIs (Level 2)
    DataFlowNode("api_or", "OR Analytics API", "api", "online", "LP, PERT, EOQ endpoints", "cell"),
    DataFlowNode("api_recon", "Reconciliation API", "api", "stale", "Bank recon automation", "cell"),
    DataFlowNode("api_einv", "E-Invoice API", "api", "online", "ETA e-invoice integration", "cell"),
]

FLOW_EDGES = [
    # Brain to Organs
    DataFlowEdge("brain", "ih_organ", "flowing", "commands", "Brain controls IH organ"),
    DataFlowEdge("brain", "ec_organ", "flowing", "commands", "Brain controls EventCore organ"),
    DataFlowEdge("brain", "or_organ", "flowing", "commands", "Brain controls OR organ"),
    DataFlowEdge("brain", "scm_organ", "error", "commands", "SCM organ not responding"),
    DataFlowEdge("brain", "aals_organ", "flowing", "commands", "Brain controls AALS organ"),

    # Organs to Database
    DataFlowEdge("ih_organ", "db_clients", "flowing", "reads/writes", "IH manages clients"),
    DataFlowEdge("ih_organ", "db_events", "flowing", "reads/writes", "IH manages events"),
    DataFlowEdge("ih_organ", "db_bnk", "stale", "reads/writes", "Bank data stale"),
    DataFlowEdge("ec_organ", "db_events", "flowing", "reads/writes", "EventCore shares events"),
    DataFlowEdge("or_organ", "db_coa", "flowing", "reads", "OR reads COA for analysis"),

    # Database to Files
    DataFlowEdge("db_clients", "file_mtbls", "flowing", "sync", "Clients synced from Excel"),
    DataFlowEdge("db_bnk", "file_bnk", "stale", "import", "Bank TXNs from Excel (stale)"),
    DataFlowEdge("db_bnk", "file_subkey", "flowing", "lookup", "Sub-key mapping active"),

    # APIs
    DataFlowEdge("or_organ", "api_or", "flowing", "serves", "OR serves analytics API"),
    DataFlowEdge("ih_organ", "api_recon", "stale", "serves", "Recon API needs refresh"),
    DataFlowEdge("ih_organ", "api_einv", "flowing", "serves", "E-invoice API active"),
]

# ═════════════════════════════════════════════════════════════════════════════
#  DATA FLOW ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class DataFlowEngine:
    def __init__(self):
        self._running = True
        self._snapshots: List[DataFlowSnapshot] = []
        self._latest: Optional[DataFlowSnapshot] = None
        self._lock = asyncio.Lock()

    def start_background_monitor(self):
        pass  # Background tasks handled by lifespan

    def capture_snapshot(self) -> DataFlowSnapshot:
        nodes = [asdict(n) for n in FLOW_TOPOLOGY]
        edges = []
        for e in FLOW_EDGES:
            edges.append({
                "from": e.from_node,
                "to": e.to_node,
                "status": e.status,
                "label": e.label,
                "description": e.description,
            })

        # Calculate health scores
        total_nodes = len(nodes)
        online_nodes = sum(1 for n in nodes if n["status"] in ("online", "flowing"))
        flow_health = int((online_nodes / total_nodes) * 100) if total_nodes else 0

        total_edges = len(edges)
        flowing_edges = sum(1 for e in edges if e["status"] == "flowing")
        data_health = int((flowing_edges / total_edges) * 100) if total_edges else 0

        # Master tables (simulated)
        master_tables = self._generate_master_tables()
        master_health = int(sum(m.health_score for m in master_tables) / len(master_tables)) if master_tables else 0

        # Alerts
        alerts = self._generate_alerts(nodes, edges, master_tables)

        # Data locations
        locations = self._generate_locations()

        snap = DataFlowSnapshot(
            timestamp=datetime.now().isoformat(),
            overall_flow_health=flow_health,
            overall_data_health=data_health,
            overall_master_health=master_health,
            critical_alerts=[asdict(a) if hasattr(a, '__dataclass_fields__') else a for a in alerts],
            nodes=nodes,
            edges=edges,
            master_tables=[asdict(m) for m in master_tables],
            data_locations=[asdict(l) for l in locations],
        )

        self._latest = snap
        self._snapshots.append(snap)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        return snap

    def _generate_master_tables(self) -> List[MasterTableHealth]:
        tables = [
            MasterTableHealth("clients", "IH", 245, 0, 2, 98, "No action needed", datetime.now().isoformat()),
            MasterTableHealth("vendors", "IH", 89, 0, 0, 100, "No action needed", datetime.now().isoformat()),
            MasterTableHealth("events", "IH/EC", 1567, 3, 12, 94, "Review duplicate events", datetime.now().isoformat()),
            MasterTableHealth("bank_transactions", "IH", 2501, 0, 45, 87, "45 null sub-ledger codes", datetime.now().isoformat()),
            MasterTableHealth("coa", "Core", 142, 0, 0, 100, "No action needed", datetime.now().isoformat()),
            MasterTableHealth("staff", "Core", 34, 0, 1, 97, "1 null email", datetime.now().isoformat()),
            MasterTableHealth("items", "IH", 523, 2, 8, 95, "Review item duplicates", datetime.now().isoformat()),
            MasterTableHealth("pnr_dim", "IH", 18, 0, 0, 100, "No action needed", datetime.now().isoformat()),
            MasterTableHealth("budget_lines", "IH", 96, 0, 0, 100, "No action needed", datetime.now().isoformat()),
            MasterTableHealth("sales_invoices", "IH", 445, 1, 3, 96, "Review 1 duplicate", datetime.now().isoformat()),
        ]
        return tables

    def _generate_alerts(self, nodes, edges, masters):
        alerts = []
        for n in nodes:
            if n["status"] == "offline":
                alerts.append({
                    "severity": "CRITICAL",
                    "title": f"{n['label']} is offline",
                    "description": f"The {n['label']} module is not responding. Check service status.",
                    "module": n["label"],
                    "timestamp": datetime.now().isoformat(),
                })
            elif n["status"] == "stale":
                alerts.append({
                    "severity": "WARNING",
                    "title": f"{n['label']} data is stale",
                    "description": f"Data in {n['label']} has not been refreshed recently.",
                    "module": n["label"],
                    "timestamp": datetime.now().isoformat(),
                })
        for e in edges:
            if e["status"] == "error":
                alerts.append({
                    "severity": "CRITICAL",
                    "title": f"Flow error: {e['from']} → {e['to']}",
                    "description": f"Data flow between {e['from']} and {e['to']} is broken: {e['description']}",
                    "module": e["from"],
                    "timestamp": datetime.now().isoformat(),
                })
            elif e["status"] == "stale":
                alerts.append({
                    "severity": "WARNING",
                    "title": f"Stale flow: {e['from']} → {e['to']}",
                    "description": f"Data flow {e['description']} needs refresh.",
                    "module": e["from"],
                    "timestamp": datetime.now().isoformat(),
                })
        for m in masters:
            if m.health_score < 90:
                alerts.append({
                    "severity": "WARNING" if m.health_score >= 70 else "CRITICAL",
                    "title": f"{m.table_name} health degraded ({m.health_score}%)",
                    "description": m.recommendation,
                    "module": m.module,
                    "timestamp": datetime.now().isoformat(),
                })
        return alerts

    def _generate_locations(self) -> List[DataLocation]:
        return [
            DataLocation("Clients", "IH", "database", "PostgreSQL: bio_erp.clients", "healthy", 245, datetime.now().isoformat()),
            DataLocation("Vendors", "IH", "database", "PostgreSQL: bio_erp.vendors", "healthy", 89, datetime.now().isoformat()),
            DataLocation("Events", "IH/EC", "database", "PostgreSQL: bio_erp.events", "healthy", 1567, datetime.now().isoformat()),
            DataLocation("Bank TXNs", "IH", "database", "PostgreSQL: bio_erp.bnk_transactions", "stale", 2501, (datetime.now() - timedelta(hours=48)).isoformat()),
            DataLocation("COA", "Core", "database", "PostgreSQL: bio_erp.coa", "healthy", 142, datetime.now().isoformat()),
            DataLocation("Master Data", "IH", "file", "D:/Data_Base_Mtbls.xlsx", "healthy", 1751, datetime.now().isoformat()),
            DataLocation("Bank Source", "IH", "file", "D:/Bnk_TRNX SOURCE.xlsx", "stale", 2501, (datetime.now() - timedelta(hours=72)).isoformat()),
            DataLocation("Sub-Key Map", "IH", "file", "D:/Bnk_Trnx_Sub_Key.xlsx", "healthy", 0, datetime.now().isoformat()),
            DataLocation("OR Analytics", "OR", "api", "http://localhost:8000/api/v1/or/", "healthy", None, datetime.now().isoformat()),
            DataLocation("E-Invoice", "IH", "api", "http://localhost:9001/api/einv/", "healthy", None, datetime.now().isoformat()),
        ]

    def get_snapshot(self) -> Optional[DataFlowSnapshot]:
        return self._latest

    def get_history(self, count: int = 10) -> List[DataFlowSnapshot]:
        return self._snapshots[-count:]

# ═════════════════════════════════════════════════════════════════════════════
#  MODULE STATUS CHECKER
# ═════════════════════════════════════════════════════════════════════════════

async def check_module_status(config: dict) -> dict:
    """Check if a module is online by attempting to connect to its port."""
    import socket
    port = config.get("port")
    if not port:
        return {**config, "status": "unknown", "health": 0, "last_seen": None}

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("localhost", port),
            timeout=2.0
        )
        writer.close()
        await writer.wait_closed()
        return {
            **config,
            "status": "online",
            "health": 98,
            "last_seen": datetime.now().isoformat(),
        }
    except Exception:
        return {
            **config,
            "status": "offline",
            "health": 0,
            "last_seen": None,
        }

# ═════════════════════════════════════════════════════════════════════════════
#  FILE SCANNER
# ═════════════════════════════════════════════════════════════════════════════

def scan_document_files() -> List[DocumentFile]:
    """Scan known file paths and return health status."""
    files = []
    now = time.time()

    for path in KNOWN_FILES:
        if path.exists():
            stat = path.stat()
            age_hours = (now - stat.st_mtime) / 3600
            status = "healthy" if age_hours < 24 else "stale" if age_hours < 168 else "missing"

            # Try to get record count from filename hints
            records = None
            sheets = None
            if "Mtbls" in path.name:
                records = 1751
                sheets = 13
            elif "TRNX" in path.name and "SOURCE" in path.name:
                records = 2501
                sheets = 1
            elif "Sub_Key" in path.name:
                records = 0
                sheets = 1

            files.append(DocumentFile(
                name=path.name,
                path=str(path),
                size_mb=round(stat.st_size / 1024 / 1024, 2),
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                staleness_hours=round(age_hours, 1),
                status=status,
                records=records,
                sheets=sheets,
            ))
        else:
            files.append(DocumentFile(
                name=path.name,
                path=str(path),
                size_mb=0,
                last_modified=None,
                staleness_hours=9999,
                status="missing",
                records=None,
                sheets=None,
            ))

    # Also scan staging directory
    if STAGING_DIR.exists():
        for f in STAGING_DIR.glob("*.xlsx"):
            stat = f.stat()
            age_hours = (now - stat.st_mtime) / 3600
            files.append(DocumentFile(
                name=f.name,
                path=str(f),
                size_mb=round(stat.st_size / 1024 / 1024, 2),
                last_modified=datetime.fromtimestamp(stat.mtime).isoformat(),
                staleness_hours=round(age_hours, 1),
                status="healthy" if age_hours < 24 else "stale",
                records=None,
                sheets=None,
            ))

    return files

# ═════════════════════════════════════════════════════════════════════════════
#  FASTAPI APPLICATION
# ═════════════════════════════════════════════════════════════════════════════

flow_engine = DataFlowEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    flow_engine.start_background_monitor()
    asyncio.create_task(_initial_snapshot())
    asyncio.create_task(_ws_broadcast_loop())
    yield
    flow_engine._running = False

async def _initial_snapshot():
    await asyncio.sleep(0.5)
    flow_engine.capture_snapshot()

async def _ws_broadcast_loop():
    while flow_engine._running:
        await asyncio.sleep(30)
        snap = flow_engine.get_snapshot()
        if snap:
            await manager.broadcast({
                "type": "snapshot",
                "payload": {
                    "timestamp": snap.timestamp,
                    "overall_flow_health": snap.overall_flow_health,
                    "overall_data_health": snap.overall_data_health,
                    "overall_master_health": snap.overall_master_health,
                    "critical_alerts": snap.critical_alerts,
                }
            })

app = FastAPI(
    title="ERP IH Launcher — Part 4 P1",
    description="Neural Graph Theme + Module Launcher + Document Manager",
    version="4.1.0",
    lifespan=lifespan,
)

# ═════════════════════════════════════════════════════════════════════════════
#  WEBSOCKET MANAGER
# ═════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ═════════════════════════════════════════════════════════════════════════════
#  HTML DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

def _load_dashboard_html() -> str:
    if DASHBOARD_HTML_PATH.exists():
        return DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
    return f"""<html><body style="font-family:system-ui;padding:40px;text-align:center;">
    <h1>🌊 ERP IH Launcher P4</h1>
    <p>dashboard_part4_p1.html not found at:<br><code>{DASHBOARD_HTML_PATH}</code></p>
    <p>Expected in same folder as this script.</p>
    </body></html>"""

@app.get("/", response_class=HTMLResponse)
async def root_dashboard():
    return HTMLResponse(content=_load_dashboard_html())

# ═════════════════════════════════════════════════════════════════════════════
#  LAUNCHER STATUS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/status")
async def launcher_status():
    snap = flow_engine.get_snapshot()
    return {
        "launcher": "ERP IH Launcher Part 4 P1",
        "version": "4.1.0",
        "port": 9003,
        "status": "running",
        "websocket_clients": len(manager.active_connections),
        "last_snapshot": snap.timestamp if snap else None,
        "features": ["neural_graph", "module_launcher", "document_manager", "ai_insights"],
    }

# ═════════════════════════════════════════════════════════════════════════════
#  MODULES API — P1 FEATURE
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/modules")
async def get_modules():
    """Return live status for all ERP modules."""
    tasks = [check_module_status(m) for m in MODULES_CONFIG]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    modules = []
    for r in results:
        if isinstance(r, Exception):
            continue
        modules.append({
            "id": r["id"],
            "name": r["name"],
            "emoji": r["emoji"],
            "role": r["role"],
            "status": r["status"],
            "health": r["health"],
            "port": r["port"],
            "url": r["url"],
            "api_docs": r["api_docs"],
            "last_seen": r["last_seen"],
        })
    return {"modules": modules}

# ═════════════════════════════════════════════════════════════════════════════
#  FLOW API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/flow/snapshot")
async def get_flow_snapshot():
    snap = flow_engine.get_snapshot()
    if not snap:
        return JSONResponse({"error": "No snapshot available"}, status_code=503)
    return asdict(snap)

@app.post("/flow/snapshot")
async def post_flow_snapshot():
    snap = flow_engine.capture_snapshot()
    return asdict(snap)

@app.get("/flow/graph")
async def get_flow_graph():
    snap = flow_engine.get_snapshot()
    if not snap:
        return {"nodes": [], "edges": []}
    return {"nodes": snap.nodes, "edges": snap.edges}

@app.get("/flow/nodes")
async def get_flow_nodes():
    snap = flow_engine.get_snapshot()
    return {"nodes": snap.nodes if snap else []}

@app.get("/flow/edges")
async def get_flow_edges():
    snap = flow_engine.get_snapshot()
    return {"edges": snap.edges if snap else []}

# ═════════════════════════════════════════════════════════════════════════════
#  LOCATIONS API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/locations")
async def get_locations():
    snap = flow_engine.get_snapshot()
    return {"locations": snap.data_locations if snap else []}

@app.get("/locations/{name}")
async def get_location(name: str):
    snap = flow_engine.get_snapshot()
    if not snap:
        return JSONResponse({"error": "No data"}, status_code=503)
    for loc in snap.data_locations:
        if loc.get("entity_name", "").lower() == name.lower():
            return loc
    return JSONResponse({"error": "Not found"}, status_code=404)

@app.get("/locations/map")
async def get_location_map():
    snap = flow_engine.get_snapshot()
    if not snap:
        return {"modules": {}}
    modules = {}
    for loc in snap.data_locations:
        mod = loc.get("primary_module", "Unknown")
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(loc)
    return {"modules": modules}

# ═════════════════════════════════════════════════════════════════════════════
#  MASTER TABLES API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/master-tables")
async def get_master_tables():
    snap = flow_engine.get_snapshot()
    return {"tables": snap.master_tables if snap else []}

@app.get("/master-tables/{name}")
async def get_master_table(name: str):
    snap = flow_engine.get_snapshot()
    if not snap:
        return JSONResponse({"error": "No data"}, status_code=503)
    for t in snap.master_tables:
        if t.get("table_name", "").lower() == name.lower():
            return t
    return JSONResponse({"error": "Not found"}, status_code=404)

@app.get("/master-tables/summary")
async def get_master_summary():
    snap = flow_engine.get_snapshot()
    if not snap or not snap.master_tables:
        return {"total_tables": 0, "by_module": {}, "overall_health": 0}
    by_module = {}
    for t in snap.master_tables:
        mod = t.get("module", "Unknown")
        if mod not in by_module:
            by_module[mod] = {"count": 0, "health": 0}
        by_module[mod]["count"] += 1
        by_module[mod]["health"] += t.get("health_score", 0)
    for mod in by_module:
        by_module[mod]["health"] = int(by_module[mod]["health"] / by_module[mod]["count"])
    overall = int(sum(t.get("health_score", 0) for t in snap.master_tables) / len(snap.master_tables))
    return {
        "total_tables": len(snap.master_tables),
        "by_module": by_module,
        "overall_health": overall,
    }

@app.post("/master-tables/refresh")
async def refresh_master_tables():
    snap = flow_engine.capture_snapshot()
    return {"message": "Master tables refreshed", "tables": len(snap.master_tables)}

# ═════════════════════════════════════════════════════════════════════════════
#  DOCUMENTS API — P1 FEATURE
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/files")
async def get_files():
    """Scan known ERP data files and return health status."""
    files = scan_document_files()
    return {"files": [asdict(f) for f in files]}

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle drag-and-drop upload to staging area."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = STAGING_DIR / file.filename
    try:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return {
            "filename": file.filename,
            "saved_to": str(dest),
            "size_mb": round(dest.stat().st_size / 1024 / 1024, 2),
            "status": "uploaded",
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ═════════════════════════════════════════════════════════════════════════════
#  AI INSIGHTS API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/ai/insights")
async def get_ai_insights():
    """Generate AI insights from current snapshot data."""
    snap = flow_engine.get_snapshot()
    if not snap:
        return {"summary": "No data available", "insights": [], "actions": []}

    insights = []
    actions = []

    # Flow health insight
    if snap.overall_flow_health < 60:
        insights.append({
            "type": "critical",
            "title": "Flow Health Degraded",
            "description": f"Overall flow health is {snap.overall_flow_health}%. Several nodes are offline or stale.",
        })
        actions.append({"label": "View Flow", "action": "switchTab('flow')"})

    # Master health insight
    if snap.overall_master_health < 80:
        insights.append({
            "type": "warning",
            "title": "Master Tables Need Attention",
            "description": f"Master table health is {snap.overall_master_health}%. Review stale tables.",
        })
        actions.append({"label": "View Masters", "action": "switchTab('master')"})

    # Alert insight
    critical_count = sum(1 for a in snap.critical_alerts if a.get("severity") == "CRITICAL")
    if critical_count > 0:
        insights.append({
            "type": "critical",
            "title": f"{critical_count} Critical Alert(s)",
            "description": "Critical issues require immediate attention.",
        })
        actions.append({"label": "View Alerts", "action": "switchTab('alerts')"})

    # Document insight
    files = scan_document_files()
    stale_files = [f for f in files if f.status == "stale"]
    if stale_files:
        insights.append({
            "type": "warning",
            "title": f"{len(stale_files)} Stale Document(s)",
            "description": f"{', '.join(f.name for f in stale_files)} need refreshing.",
        })
        actions.append({"label": "View Documents", "action": "switchTab('documents')"})

    # Positive insight
    if snap.overall_flow_health >= 80 and snap.overall_master_health >= 90 and not critical_count:
        insights.append({
            "type": "info",
            "title": "System Healthy",
            "description": "All systems operating normally. No action required.",
        })

    overall = int((snap.overall_flow_health + snap.overall_data_health + snap.overall_master_health) / 3)
    return {
        "summary": f"System health is {overall}%. {len(insights)} insight(s) available.",
        "insights": insights,
        "actions": actions,
        "timestamp": snap.timestamp,
    }

# ═════════════════════════════════════════════════════════════════════════════
#  SUB-APP FACTORY (for mounting into main BIO-ERP)
# ═════════════════════════════════════════════════════════════════════════════

def create_v4_app() -> FastAPI:
    """Factory function to create the Part 4 P1 sub-app."""
    return app

# ═════════════════════════════════════════════════════════════════════════════
#  STANDALONE ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  ERP IH Launcher — Part 4 P1: Neural Graph + Modules + Documents")
    print("  Port: 9003  |  Dashboard: http://localhost:9003")
    print("  Features: Neural Graph | Module Launcher | Document Manager | AI Insights")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=9003)
