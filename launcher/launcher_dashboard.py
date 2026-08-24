#!/usr/bin/env python3
"""
ERP IH — System Launcher & Diagnostic Dashboard v3.1
Port: 9002 | Features: Health Monitor, Gap Scanner, AI Chatbot,
Data Flow, Data Locations, Master Table Health Monitor
"""

import os, sys, json, time, socket, asyncio, threading, subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from collections import defaultdict
import re, urllib.request, urllib.error

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── CONFIGURATION ───────────────────────────────────────────────────────────

BASE_DIR = Path("D:/ERP System/BIO_ERP")
IH_DIR = BASE_DIR
SCAN_INTERVAL = 30
ENDPOINT_TIMEOUT = 5

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "bio_erp"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.environ["DB_PASSWORD"],  # required — fail loud, no default
}

MODULES = {
    "bio_erp_core": {
        "name": "BIO-ERP Core", "port": 8000, "path": BASE_DIR,
        "required_files": ["app/main.py", "app/models.py", "requirements.txt"],
        "health_endpoint": "/api/v1/health", "critical": True,
        "db_tables": ["organs", "cells", "neural_nodes", "audit_trail", "events"],
    },
    "event_core": {
        "name": "EventCore ERP", "port": 8001,
        "path": BASE_DIR,
        "required_files": ["main.py", "models.py"],
        "health_endpoint": "/health", "critical": True,
        "db_tables": ["events", "event_line_items", "venues", "clients"],
    },
    "or_module": {
        "name": "OR-ERP Module", "port": 8000,
        "path": BASE_DIR / "app" / "or_module",
        "required_files": ["or_erp_module.py", "sub_app.py"],
        "health_endpoint": "/api/v1/or/health", "critical": False,
        "db_tables": ["or_analyses", "or_scenarios", "or_results"],
    },
    "scm_module": {
        "name": "SCM Module", "port": None,
        "path": BASE_DIR / "app" / "scm_module",
        "required_files": [], "health_endpoint": None, "critical": False,
        "db_tables": ["scm_staging", "cost_analyses", "vendor_evaluations"],
    },
    "incentivehouse": {
        "name": "IncentiveHouse ERP", "port": 9001,
        "path": BASE_DIR,
        "required_files": ["launcher/start_server.py"],
        "health_endpoint": "/health", "critical": True,
        "db_tables": ["events", "work_orders", "sales_line_items", "bnk_transactions",
                      "clients", "suppliers", "cost_centers", "staff"],
    },
    "ih_bank_recon": {
        "name": "IH Bank Reconciliation", "port": 9001,
        "path": BASE_DIR,
        "required_files": ["routers/bank_recon.py"],
        "health_endpoint": "/api/v1/bnk/status", "critical": False,
        "db_tables": ["bnk_reconciliation", "bnk_transactions"],
    },
    "ih_sales": {
        "name": "IH Sales Module", "port": 9001,
        "path": BASE_DIR,
        "required_files": ["routers/sales.py"],
        "health_endpoint": "/api/v1/sal/summary", "critical": False,
        "db_tables": ["sales_invoices", "sales_line_items"],
    },
    "database": {
        "name": "PostgreSQL Database", "port": 5432, "path": None,
        "required_files": [], "health_endpoint": None, "critical": True,
    },
    "redis": {
        "name": "Redis Cache", "port": 6379, "path": None,
        "required_files": [], "health_endpoint": None, "critical": False,
    },
}

START_TIME = time.time()

# ── DATA CLASSES ────────────────────────────────────────────────────────────

@dataclass
class ModuleStatus:
    id: str; name: str; status: str; port: Optional[int]; pid: Optional[int]
    uptime_seconds: Optional[float]; last_check: str
    response_time_ms: Optional[float]; error_message: Optional[str]
    file_integrity: Dict[str, bool]; endpoint_status: Dict[str, Any]
    critical: bool; health_score: int
    db_table_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self): return asdict(self)

@dataclass
class GapFinding:
    severity: str; category: str; module: str; description: str
    file_path: Optional[str]; line_number: Optional[int]
    recommendation: str; erp_builder_compliance: Optional[str]

@dataclass
class DataFlowEdge:
    source: str; target: str; flow_type: str
    tables: List[str]; status: str; throughput: Optional[int]

@dataclass
class DataLocation:
    location_id: str; location_type: str  # db, file, cache, staging
    path: str; size_bytes: Optional[int]; row_count: Optional[int]
    last_updated: Optional[str]; status: str

@dataclass
class MasterTableHealth:
    table_name: str; schema: str; row_count: int; estimated_size: str
    last_analyzed: Optional[str]; last_updated: Optional[str]
    has_primary_key: bool; has_indexes: bool; health_score: int
    sync_status: str  # synced, pending, lagging, unknown

@dataclass
class SystemScanResult:
    timestamp: str; overall_health_score: int
    modules_scanned: int; modules_healthy: int
    modules_degraded: int; modules_down: int
    total_endpoints: int; tested_endpoints: int; documented_endpoints: int
    gap_findings: List[GapFinding]; scan_duration_ms: float
    recommendations: List[str]

# ── SYSTEM SCANNER ──────────────────────────────────────────────────────────

class SystemScanner:
    def __init__(self):
        self.scan_history: List[SystemScanResult] = []
        self.current_status: Dict[str, ModuleStatus] = {}
        self._lock = threading.Lock()
        self._running = False
        self._db_conn = None
        self._connect_db()

    def _connect_db(self):
        if not DB_AVAILABLE: return
        try:
            self._db_conn = psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"[DB] Connect failed: {e}")

    def _db_query(self, sql: str, params: tuple = ()):
        if not self._db_conn: return []
        try:
            with self._db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except Exception as e:
            err = str(e)
            if "aborted" in err or "does not exist" in err:
                self._db_conn.rollback()
            print(f"[DB] Query error: {e}")
            return []

    def start_background_scanner(self):
        self._running = True
        t = threading.Thread(target=self._scan_loop, daemon=True)
        t.start()
        return t

    def _scan_loop(self):
        while self._running:
            try:
                self.run_full_scan()
            except Exception as e:
                print(f"[SCANNER] {e}")
            time.sleep(SCAN_INTERVAL)

    def run_full_scan(self) -> SystemScanResult:
        start = time.time()
        findings: List[GapFinding] = []
        module_results = {}

        for mid, mc in MODULES.items():
            st = self._check_module(mid, mc)
            module_results[mid] = st
            if st.status == "down" and st.critical:
                findings.append(GapFinding("critical", "missing_endpoint", mc["name"],
                    f"Critical module {mc['name']} is DOWN on port {mc.get('port', 'N/A')}",
                    None, None, f"Start: cd {mc.get('path', 'N/A')} && python main.py", "P0"))
            elif st.status == "degraded":
                findings.append(GapFinding("high", "performance", mc["name"],
                    f"Module {mc['name']} degraded. Response: {st.response_time_ms}ms",
                    None, None, "Check resource usage and restart", "P0"))

        # File integrity
        for mid, mc in MODULES.items():
            if mc.get("path"):
                findings.extend(self._scan_file_integrity(mid, mc))

        # Security scan
        findings.extend(self._scan_security())

        # P0 compliance
        findings.extend(self._scan_erp_compliance())

        healthy = sum(1 for m in module_results.values() if m.status == "healthy")
        total = len(module_results)
        health_score = int((healthy / total) * 100) if total else 0
        critical_down = sum(1 for m in module_results.values() if m.status == "down" and m.critical)
        health_score = max(0, health_score - critical_down * 25)

        recs = []
        c = sum(1 for f in findings if f.severity == "critical")
        if c: recs.append(f"URGENT: {c} critical issues. Address immediately.")
        down_mods = [m.name for m in module_results.values() if m.status == "down"]
        if down_mods: recs.append(f"Restart required: {', '.join(down_mods)}")
        sec = [f for f in findings if f.category == "security"]
        if sec: recs.append(f"{len(sec)} security vulnerabilities found.")
        recs.append(f"System Health: {healthy}/{total} modules healthy")

        result = SystemScanResult(
            timestamp=datetime.now().isoformat(),
            overall_health_score=health_score,
            modules_scanned=total, modules_healthy=healthy,
            modules_degraded=sum(1 for m in module_results.values() if m.status == "degraded"),
            modules_down=sum(1 for m in module_results.values() if m.status == "down"),
            total_endpoints=0, tested_endpoints=0, documented_endpoints=0,
            gap_findings=findings,
            scan_duration_ms=round((time.time() - start) * 1000, 2),
            recommendations=recs)

        with self._lock:
            self.current_status = module_results
            self.scan_history.append(result)
            if len(self.scan_history) > 100:
                self.scan_history = self.scan_history[-100:]

        return result

    def _check_module(self, mid: str, mc: dict) -> ModuleStatus:
        port = mc.get("port")
        path = mc.get("path")
        hep = mc.get("health_endpoint")
        status = "unknown"; resp_time = None; err = None
        pid = None; uptime = None; hscore = 0; fi = {}

        if port:
            open_, pt = self._check_port(port)
            if open_:
                if hep:
                    ok, rt, body = self._check_http(port, hep)
                    if ok:
                        status = "healthy"; resp_time = rt; hscore = 100
                        try:
                            d = json.loads(body); uptime = d.get("uptime_seconds")
                        except: pass
                    else:
                        status = "degraded"; resp_time = rt; hscore = 50
                        err = f"Health endpoint error"
                else:
                    status = "healthy"; resp_time = pt; hscore = 80
            else:
                status = "down"; err = f"Port {port} not responding"; hscore = 0
        else:
            status = "unknown"; hscore = 50

        if path and mc.get("required_files"):
            for rf in mc["required_files"]:
                fp = path / rf
                fi[str(rf)] = fp.exists()

        if fi:
            iscore = sum(fi.values()) / len(fi) * 100
            hscore = int((hscore + iscore) / 2)

        if port:
            pid = self._get_pid(port)

        # DB table counts
        db_counts = {}
        for tbl in mc.get("db_tables", []):
            rows = self._db_query(f"SELECT COUNT(*) as cnt FROM {tbl}")
            if rows:
                db_counts[tbl] = rows[0]["cnt"]

        return ModuleStatus(id=mid, name=mc["name"], status=status, port=port, pid=pid,
            uptime_seconds=uptime, last_check=datetime.now().isoformat(),
            response_time_ms=round(resp_time, 2) if resp_time else None,
            error_message=err, file_integrity=fi, endpoint_status={},
            critical=mc.get("critical", False), health_score=hscore,
            db_table_counts=db_counts)

    def _check_port(self, port: int, host: str = "127.0.0.1"):
        t = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(ENDPOINT_TIMEOUT)
            r = s.connect_ex((host, port))
            s.close()
            return r == 0, (time.time() - t) * 1000
        except:
            return False, None

    def _check_http(self, port: int, ep: str, host: str = "127.0.0.1"):
        url = f"http://{host}:{port}{ep}"
        t = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "ERP-IH-Scanner/3.0")
            with urllib.request.urlopen(req, timeout=ENDPOINT_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return resp.status < 400, (time.time() - t) * 1000, body
        except Exception as e:
            return False, (time.time() - t) * 1000, str(e)

    def _get_pid(self, port: int):
        try:
            if sys.platform == "win32":
                r = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                    capture_output=True, text=True, timeout=5)
                for line in r.stdout.split("\n"):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5: return int(parts[-1])
            else:
                r = subprocess.run(["lsof", "-ti", f"tcp:{port}"],
                    capture_output=True, text=True, timeout=5)
                if r.stdout.strip(): return int(r.stdout.strip().split("\n")[0])
        except: pass
        return None

    def _scan_file_integrity(self, mid: str, mc: dict):
        findings = []
        p = mc.get("path")
        if not p: return findings
        for sf in [".env", "config.py"]:
            sp = p / sf
            if sp.exists():
                content = sp.read_text(errors="ignore")
                if re.search(r'password\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                    findings.append(GapFinding("high", "security", mc["name"],
                        f"Hardcoded password in {sf}", str(sp), None,
                        "Move to environment variables", "P0"))
        py_files = list(p.rglob("*.py")) if p.exists() else []
        for pyf in py_files[:30]:
            try:
                compile(pyf.read_text(errors="ignore"), str(pyf), "exec")
            except SyntaxError as e:
                findings.append(GapFinding("critical", "missing_endpoint", mc["name"],
                    f"Syntax error in {pyf.name}: {e.msg}", str(pyf), e.lineno,
                    "Fix syntax error", "P0"))
        return findings

    def _scan_security(self):
        findings = []
        for mid, mc in MODULES.items():
            p = mc.get("path")
            if not p: continue
            for mf in list(p.rglob("main.py")) + list(p.rglob("config.py"))[:5]:
                if not mf.exists(): continue
                content = mf.read_text(errors="ignore")
                if re.search(r'debug\s*=\s*True', content):
                    findings.append(GapFinding("high", "security", mc["name"],
                        f"Debug mode in {mf.name}", str(mf), None,
                        "Set debug=False in production", "P0"))
                if "allow_origins=['*']" in content or 'allow_origins=["*"]' in content:
                    findings.append(GapFinding("medium", "security", mc["name"],
                        "CORS allows all origins", str(mf), None,
                        "Restrict CORS to specific domains", "P1"))
        return findings

    def _scan_erp_compliance(self):
        findings = []
        p0_checks = {"Auth": ["auth", "login", "jwt", "password_hash"],
                      "Audit": ["audit_trail", "audit.log", "AuditTrail"],
                      "Backup": ["backup", "restore", "dump"],
                      "Variance": ["variance", "reconciliation"]}
        for mid, mc in MODULES.items():
            p = mc.get("path")
            if not p or not p.exists(): continue
            all_py = ""
            for pyf in p.rglob("*.py"):
                try: all_py += pyf.read_text(errors="ignore") + "\n"
                except: pass
            for name, kws in p0_checks.items():
                if not any(kw in all_py for kw in kws):
                    findings.append(GapFinding("critical", "missing_endpoint", mc["name"],
                        f"P0 Gap: {name} system not detected", None, None,
                        f"Implement {name} per ERP Builder Protocol v2.2", "P0"))
        return findings

# ── DATA FLOW ANALYZER ──────────────────────────────────────────────────────

class DataFlowAnalyzer:
    def __init__(self, scanner: SystemScanner):
        self.scanner = scanner

    def get_flows(self) -> List[DataFlowEdge]:
        edges = []
        tbl_map = {
            "events": ("incentivehouse", "event_core"),
            "clients": ("incentivehouse", "bio_erp_core"),
            "suppliers": ("incentivehouse", "bio_erp_core"),
            "sales_invoices": ("incentivehouse", "ih_sales"),
            "bnk_transactions": ("incentivehouse", "ih_bank_recon"),
            "cost_centers": ("incentivehouse", "or_module"),
            "scm_staging": ("scm_module", "incentivehouse"),
        }
        with self.scanner._lock:
            modules = self.scanner.current_status
        for tbl, (src, tgt) in tbl_map.items():
            s = modules.get(src, ModuleStatus(id=src, name=src, status="unknown",
                port=None, pid=None, uptime_seconds=None, last_check="",
                response_time_ms=None, error_message=None, file_integrity={},
                endpoint_status={}, critical=False, health_score=0))
            t = modules.get(tgt, ModuleStatus(id=tgt, name=tgt, status="unknown",
                port=None, pid=None, uptime_seconds=None, last_check="",
                response_time_ms=None, error_message=None, file_integrity={},
                endpoint_status={}, critical=False, health_score=0))
            status = "active" if s.status == "healthy" and t.status == "healthy" else "degraded"
            edges.append(DataFlowEdge(
                source=src, target=tgt, flow_type="db_sync",
                tables=[tbl], status=status, throughput=None))
        return edges

    def get_data_locations(self) -> List[DataLocation]:
        locations = []
        # DB locations
        with self.scanner._lock:
            modules = self.scanner.current_status
        for mid, ms in modules.items():
            if ms.db_table_counts:
                for tbl, cnt in ms.db_table_counts.items():
                    locations.append(DataLocation(
                        location_id=f"{mid}.{tbl}",
                        location_type="db",
                        path=f"bio_erp.public.{tbl}",
                        size_bytes=None, row_count=cnt,
                        last_updated=ms.last_check,
                        status="synced" if ms.status == "healthy" else "stale"))
        # File locations
        for mid, mc in MODULES.items():
            p = mc.get("path")
            if p and p.exists():
                for f in ["config.py", "requirements.txt", ".env"]:
                    fp = p / f
                    if fp.exists():
                        locations.append(DataLocation(
                            location_id=f"{mid}.{f}",
                            location_type="file",
                            path=str(fp), size_bytes=fp.stat().st_size,
                            row_count=None, last_updated=datetime.fromtimestamp(
                                fp.stat().st_mtime).isoformat(),
                            status="active" if fp.exists() else "missing"))
        return locations

    def get_master_table_health(self) -> List[MasterTableHealth]:
        results = []
        tables = ["events", "clients", "suppliers", "sales_invoices", "bnk_transactions",
                  "work_orders", "cost_centers", "audit_logs", "users", "branches"]
        for tbl in tables:
            rows = self.scanner._db_query(f"""
                SELECT COUNT(*) as cnt,
                       COALESCE(pg_size_pretty(pg_total_relation_size('{tbl}')), '0 bytes') as size,
                       (SELECT MAX(last_analyze) FROM pg_stat_all_tables
                        WHERE relname = '{tbl}') as last_analyzed
                FROM {tbl}
            """)
            if rows:
                r = rows[0]
                pk = self.scanner._db_query(f"""
                    SELECT COUNT(*) as cnt FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = '{tbl}' AND c.contype = 'p'
                """)
                idx = self.scanner._db_query(f"""
                    SELECT COUNT(*) as cnt FROM pg_indexes
                    WHERE tablename = '{tbl}'
                """)
                has_pk = pk[0]["cnt"] > 0 if pk else False
                has_idx = idx[0]["cnt"] > 0 if idx else False
                hscore = 100
                if not has_pk: hscore -= 30
                if not has_idx: hscore -= 20
                if r["cnt"] == 0: hscore -= 10
                hscore = max(0, hscore)
                # Determine sync status
                with self.scanner._lock:
                    active = sum(1 for m in self.scanner.current_status.values()
                                 if m.status == "healthy")
                    total_mods = len(self.scanner.current_status)
                    sync_status = "synced" if active >= total_mods / 2 else "degraded"
                results.append(MasterTableHealth(
                    table_name=tbl, schema="public",
                    row_count=r["cnt"], estimated_size=r["size"] or "0 bytes",
                    last_analyzed=r["last_analyzed"].isoformat() if r.get("last_analyzed") else None,
                    last_updated=None, has_primary_key=has_pk,
                    has_indexes=has_idx, health_score=hscore,
                    sync_status=sync_status))
        return results

# ── AI CHATBOT ──────────────────────────────────────────────────────────────

class AIChatbot:
    def __init__(self, scanner: SystemScanner, flow_analyzer: DataFlowAnalyzer):
        self.scanner = scanner
        self.flow = flow_analyzer
        self.history: List[Dict[str, str]] = []

    def _context(self) -> str:
        with self.scanner._lock:
            modules = self.scanner.current_status
        if not modules: return "No scan data available yet."
        lines = ["Current System Status:"]
        for ms in modules.values():
            e = "\U0001f7e2" if ms.status == "healthy" else "\U0001f7e1" if ms.status == "degraded" else "\U0001f534"
            lines.append(f"{e} {ms.name}: {ms.status.upper()} (Score: {ms.health_score}/100)")
            if ms.error_message: lines.append(f"   Error: {ms.error_message}")
        if self.scanner.scan_history:
            l = self.scanner.scan_history[-1]
            lines.append(f"\nLast Scan: {l.timestamp}")
            lines.append(f"Health: {l.overall_health_score}/100 | Gaps: {len(l.gap_findings)}")
        return "\n".join(lines)

    async def chat(self, msg: str) -> str:
        self.history.append({"role": "user", "content": msg})
        q = msg.lower()
        if any(k in q for k in ["health", "status", "summary", "overview"]):
            r = self._health()
        elif any(k in q for k in ["gap", "missing", "compliance", "p0"]):
            r = self._gaps()
        elif "module" in q or any(m in q for m in ["bio", "event", "or", "scm", "incentive"]):
            r = self._module(q)
        elif any(k in q for k in ["fix", "repair", "restart"]):
            r = self._fix()
        elif any(k in q for k in ["slow", "performance", "optimize"]):
            r = self._perf()
        elif any(k in q for k in ["security", "vulnerability"]):
            r = self._security()
        elif any(k in q for k in ["data flow", "flow"]):
            r = self._data_flow()
        elif any(k in q for k in ["location", "where"]) and "data" in q:
            r = self._data_locations()
        elif any(k in q for k in ["master table", "table health", "tables"]):
            r = self._master_tables()
        else:
            r = ("I can help with:\n"
                 "- `health` — System health report\n"
                 "- `gap analysis` — Compliance scan\n"
                 "- `fix` — Repair instructions\n"
                 "- `performance` — Speed analysis\n"
                 "- `security` — Vulnerability check\n"
                 "- `data flow` — Module data movement\n"
                 "- `data locations` — Where data lives\n"
                 "- `master tables` — Table health monitor")
        self.history.append({"role": "assistant", "content": r})
        if len(self.history) > 20: self.history = self.history[-20:]
        return r

    def _health(self) -> str:
        with self.scanner._lock:
            modules = self.scanner.current_status
        h = sum(1 for m in modules.values() if m.status == "healthy")
        t = len(modules)
        score = int(h / t * 100) if t else 0
        lines = [f"## System Health Report (Score: {score}/100)",
                 f"**Modules Online:** {h}/{t}", "", "### Module Breakdown:"]
        for ms in sorted(modules.values(), key=lambda x: x.health_score, reverse=True):
            icon = "\u2705" if ms.status == "healthy" else "\u26a0\ufe0f" if ms.status == "degraded" else "\u274c"
            lines.append(f"{icon} **{ms.name}** — {ms.status.upper()} | Score: {ms.health_score}/100 | Port: {ms.port or 'N/A'}")
            if ms.response_time_ms: lines.append(f"   Response: {ms.response_time_ms}ms")
            if ms.error_message: lines.append(f"   Issue: {ms.error_message}")
        if self.scanner.scan_history:
            lines.append("\n### Top Recommendations:")
            for rec in self.scanner.scan_history[-1].recommendations[:5]:
                lines.append(f"- {rec}")
        return "\n".join(lines)

    def _gaps(self) -> str:
        if not self.scanner.scan_history:
            return "No scan data available."
        l = self.scanner.scan_history[-1]
        if not l.gap_findings:
            return "## No Gaps Detected\n\nSystem is fully compliant!"
        by_sev = defaultdict(list)
        for f in l.gap_findings: by_sev[f.severity].append(f)
        lines = [f"## Gap Analysis ({len(l.gap_findings)} findings)",
                 f"Health Score: {l.overall_health_score}/100", ""]
        for sev in ["critical", "high", "medium", "low"]:
            if sev in by_sev:
                lines.append(f"### {sev.upper()} ({len(by_sev[sev])})")
                for f in by_sev[sev][:5]:
                    lines.append(f"**[{f.erp_builder_compliance or 'N/A'}]** {f.description}")
                    lines.append(f"   File: `{f.file_path or 'N/A'}`")
                    lines.append(f"   Fix: {f.recommendation}\n")
        return "\n".join(lines)

    def _module(self, q: str) -> str:
        with self.scanner._lock:
            modules = self.scanner.current_status
        for ms in modules.values():
            if ms.name.lower() in q or ms.id.replace("_", " ") in q:
                lines = [f"## {ms.name} Details",
                         f"**Status:** {ms.status.upper()} | **Score:** {ms.health_score}/100",
                         f"**Port:** {ms.port or 'N/A'} | **PID:** {ms.pid or 'N/A'}",
                         f"**Last Check:** {ms.last_check}", ""]
                if ms.file_integrity:
                    lines.append("**File Integrity:**")
                    for f, ok in ms.file_integrity.items():
                        lines.append(f"  {'\u2705' if ok else '\u274c'} {f}")
                if ms.db_table_counts:
                    lines.append(f"\n**DB Tables ({len(ms.db_table_counts)}):**")
                    for tbl, cnt in ms.db_table_counts.items():
                        lines.append(f"  - {tbl}: {cnt} rows")
                if ms.error_message:
                    lines.append(f"\n**Issue:** {ms.error_message}")
                return "\n".join(lines)
        return f"Module not found. Available: {', '.join(m.name for m in modules.values())}"

    def _fix(self) -> str:
        with self.scanner._lock:
            broken = [m for m in self.scanner.current_status.values() if m.status in ("down", "degraded")]
        if not broken: return "## All Systems Operational\n\nNo fixes needed!"
        lines = ["## Repair Instructions", ""]
        for m in broken:
            mc = MODULES.get(m.id, {})
            lines.append(f"### {m.name}")
            lines.append(f"Issue: {m.error_message or 'Unknown'}")
            lines.append("Steps:")
            lines.append(f"1. cd {mc.get('path', 'N/A')}")
            if m.port: lines.append(f"2. Check port: netstat -ano | findstr :{m.port}")
            lines.append(f"3. Start: python launcher/start_server.py (or uvicorn app.main:app --port {m.port})")
            lines.append("")
        return "\n".join(lines)

    def _perf(self) -> str:
        with self.scanner._lock:
            slow = [(m.name, m.response_time_ms) for m in self.scanner.current_status.values()
                    if m.response_time_ms and m.response_time_ms > 500]
        lines = ["## Performance Analysis", ""]
        if slow:
            slow.sort(key=lambda x: x[1], reverse=True)
            lines.append("**Slow Modules:**")
            for n, rt in slow: lines.append(f"- {n}: {rt:.0f}ms (target <200ms)")
            lines.append("\n**Recommendations:**")
            lines.append("1. Enable DB connection pooling")
            lines.append("2. Add Redis caching")
            lines.append("3. Review N+1 queries in ORM")
            lines.append("4. Use async DB drivers (asyncpg)")
        else:
            lines.append("All modules within acceptable thresholds (<500ms)")
        return "\n".join(lines)

    def _security(self) -> str:
        if not self.scanner.scan_history: return "No scan data for security analysis."
        sec = [f for f in self.scanner.scan_history[-1].gap_findings if f.category == "security"]
        lines = ["## Security Assessment", ""]
        if sec:
            lines.append(f"{len(sec)} security issues found:\n")
            for f in sec:
                lines.append(f"**[{f.severity.upper()}]** {f.description}")
                lines.append(f"   File: `{f.file_path or 'N/A'}` | Fix: {f.recommendation}\n")
            lines.append("**Immediate Actions:**")
            lines.append("1. Rotate exposed credentials")
            lines.append("2. Disable debug mode in production")
            lines.append("3. Restrict CORS to known domains")
            lines.append("4. Enable HTTPS on all endpoints")
        else:
            lines.append("No security vulnerabilities detected.")
        return "\n".join(lines)

    def _data_flow(self) -> str:
        edges = self.flow.get_flows()
        lines = ["## Data Flow Map", ""]
        if not edges:
            lines.append("No data flows detected.")
            return "\n".join(lines)
        lines.append(f"{len(edges)} data flows active:\n")
        for e in edges:
            icon = "\u2705" if e.status == "active" else "\u26a0\ufe0f"
            lines.append(f"{icon} **{e.source}** \u2192 **{e.target}** ({e.flow_type})")
            lines.append(f"   Tables: {', '.join(e.tables)}")
            lines.append(f"   Status: {e.status}")
        lines.append("\n**Key Data Movement Paths:**")
        lines.append("- Events: incentivehouse -> event_core (bidirectional)")
        lines.append("- Financials: ih_sales <-> ih_bank_recon (via bnk_transactions)")
        lines.append("- Master Data: incentivehouse <-> bio_erp_core (clients, vendors)")
        return "\n".join(lines)

    def _data_locations(self) -> str:
        locs = self.flow.get_data_locations()
        lines = ["## Data Locations Map", ""]
        if not locs:
            lines.append("No data locations detected.")
            return "\n".join(lines)
        db_count = sum(1 for l in locs if l.location_type == "db")
        file_count = sum(1 for l in locs if l.location_type == "file")
        lines.append(f"**{len(locs)} data locations found** ({db_count} DB, {file_count} files)\n")
        for l_type in ["db", "file"]:
            subset = [l for l in locs if l.location_type == l_type]
            if not subset: continue
            lines.append(f"### {l_type.upper()} Locations ({len(subset)})")
            for l in subset[:10]:
                icon = "\u2705" if l.status == "active" or l.status == "synced" else "\u26a0\ufe0f"
                cnt = f" | {l.row_count} rows" if l.row_count else ""
                sz = f" | {l.size_bytes} bytes" if l.size_bytes else ""
                lines.append(f"{icon} `{l.location_id}`{cnt}{sz}")
            if len(subset) > 10:
                lines.append(f"... and {len(subset) - 10} more")
            lines.append("")
        return "\n".join(lines)

    def _master_tables(self) -> str:
        tables = self.flow.get_master_table_health()
        lines = ["## Master Table Health Monitor", ""]
        if not tables:
            lines.append("No table health data available.")
            return "\n".join(lines)
        critical = sum(1 for t in tables if t.health_score < 50)
        warning = sum(1 for t in tables if 50 <= t.health_score < 80)
        healthy = sum(1 for t in tables if t.health_score >= 80)
        lines.append(f"Healthy: {healthy} | Warning: {warning} | Critical: {critical}\n")
        for t in sorted(tables, key=lambda x: x.health_score):
            icon = "\u2705" if t.health_score >= 80 else "\u26a0\ufe0f" if t.health_score >= 50 else "\u274c"
            lines.append(f"{icon} **{t.table_name}** (Score: {t.health_score}/100)")
            lines.append(f"   Rows: {t.row_count:,} | Size: {t.estimated_size} | PK: {'Yes' if t.has_primary_key else 'No'}")
            lines.append(f"   Sync: {t.sync_status}")
        lines.append("\n**Tables Needing Attention:**")
        for t in tables:
            if not t.has_primary_key:
                lines.append(f"- {t.table_name}: Missing primary key")
            if not t.has_indexes:
                lines.append(f"- {t.table_name}: Missing indexes")
            if t.sync_status == "degraded":
                lines.append(f"- {t.table_name}: Sync degraded")
        return "\n".join(lines)

# ── FASTAPI APP ─────────────────────────────────────────────────────────────

app = FastAPI(title="ERP IH Launcher", version="3.1.0")
scanner = SystemScanner()
flow_analyzer = DataFlowAnalyzer(scanner)
chatbot = AIChatbot(scanner, flow_analyzer)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# API Endpoints
@app.get("/api/v1/launcher/health")
async def launcher_health():
    return {"status": "healthy", "version": "3.1.0",
            "uptime_seconds": time.time() - START_TIME,
            "scanner_running": scanner._running,
            "modules_monitored": len(MODULES)}

@app.get("/api/v1/launcher/modules")
async def get_modules():
    with scanner._lock:
        return {"modules": {k: v.to_dict() for k, v in scanner.current_status.items()},
                "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/launcher/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    result = scanner.run_full_scan()
    return {"message": "Scan completed",
            "result": {"timestamp": result.timestamp,
                       "overall_health_score": result.overall_health_score,
                       "modules_healthy": result.modules_healthy,
                       "modules_degraded": result.modules_degraded,
                       "modules_down": result.modules_down,
                       "gap_count": len(result.gap_findings),
                       "scan_duration_ms": result.scan_duration_ms,
                       "recommendations": result.recommendations}}

@app.get("/api/v1/launcher/gaps")
async def get_gaps():
    if not scanner.scan_history:
        return {"message": "No scan data", "gaps": []}
    l = scanner.scan_history[-1]
    return {"overall_health_score": l.overall_health_score,
            "total_findings": len(l.gap_findings),
            "findings_by_severity": {
                "critical": len([f for f in l.gap_findings if f.severity == "critical"]),
                "high": len([f for f in l.gap_findings if f.severity == "high"]),
                "medium": len([f for f in l.gap_findings if f.severity == "medium"]),
                "low": len([f for f in l.gap_findings if f.severity == "low"])},
            "findings": [{"severity": f.severity, "category": f.category,
                           "module": f.module, "description": f.description,
                           "file_path": f.file_path, "recommendation": f.recommendation,
                           "compliance": f.erp_builder_compliance} for f in l.gap_findings],
            "recommendations": l.recommendations}

@app.get("/api/v1/launcher/history")
async def get_history(limit: int = 10):
    with scanner._lock:
        history = scanner.scan_history[-limit:]
    return {"scans": [{"timestamp": h.timestamp, "health_score": h.overall_health_score,
                        "modules_healthy": h.modules_healthy, "modules_down": h.modules_down,
                        "gap_count": len(h.gap_findings), "duration_ms": h.scan_duration_ms}
                       for h in reversed(history)]}

@app.get("/api/v1/launcher/data-flows")
async def get_data_flows():
    edges = flow_analyzer.get_flows()
    return {"flows": [{"source": e.source, "target": e.target, "flow_type": e.flow_type,
                        "tables": e.tables, "status": e.status} for e in edges]}

@app.get("/api/v1/launcher/data-locations")
async def get_data_locations():
    locs = flow_analyzer.get_data_locations()
    return {"locations": [{"location_id": l.location_id, "location_type": l.location_type,
                            "path": l.path, "size_bytes": l.size_bytes,
                            "row_count": l.row_count, "last_updated": l.last_updated,
                            "status": l.status} for l in locs]}

@app.get("/api/v1/launcher/master-tables")
async def get_master_tables():
    tables = flow_analyzer.get_master_table_health()
    return {"tables": [{"table_name": t.table_name, "schema": t.schema,
                         "row_count": t.row_count, "estimated_size": t.estimated_size,
                         "has_primary_key": t.has_primary_key,
                         "has_indexes": t.has_indexes,
                         "health_score": t.health_score, "sync_status": t.sync_status}
                        for t in tables]}

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            resp = await chatbot.chat(msg)
            await ws.send_json({"type": "message", "content": resp,
                                 "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect: pass
    except Exception as e:
        await ws.send_json({"type": "error", "content": str(e),
                             "timestamp": datetime.now().isoformat()})

# ── DASHBOARD HTML ──────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERP IH — System Launcher v3.1</title>
<style>
:root{--bg:#0f172a;--bg2:#1e293b;--bg3:#334155;--fg:#f1f5f9;--fg2:#94a3b8;--grn:#22c55e;--ylw:#eab308;--red:#ef4444;--blu:#3b82f6;--pur:#a855f7;--brd:#475569}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--fg);min-height:100vh;overflow-x:hidden}
.header{background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:2px solid var(--blu);padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 4px 20px rgba(0,0,0,.4)}
.logo-sec{display:flex;align-items:center;gap:1rem}
.logo{width:48px;height:48px;background:linear-gradient(135deg,var(--blu),var(--pur));border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700}
.tit h1{font-size:1.5rem;background:linear-gradient(90deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.tit p{font-size:.85rem;color:var(--fg2)}
.act{display:flex;gap:.75rem}
.btn{padding:.6rem 1.2rem;border:none;border-radius:8px;cursor:pointer;font-size:.9rem;font-weight:600;transition:all .2s;display:flex;align-items:center;gap:.5rem}
.btn-pri{background:linear-gradient(135deg,var(--blu),#2563eb);color:#fff}
.btn-pri:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(59,130,246,.4)}
.btn-sec{background:var(--bg3);color:var(--fg);border:1px solid var(--brd)}
.btn-sec:hover{background:var(--brd)}
.main{display:grid;grid-template-columns:260px 1fr 340px;gap:1.5rem;padding:1.5rem;max-width:1920px;margin:0 auto}
@media(max-width:1400px){.main{grid-template-columns:240px 1fr 300px}}
@media(max-width:1100px){.main{grid-template-columns:1fr}.sb-right{position:fixed;bottom:0;right:0;width:100%;height:45vh;z-index:50}}
.sb-left{display:flex;flex-direction:column;gap:1rem}
.ncard{background:var(--bg2);border-radius:12px;border:1px solid var(--brd);overflow:hidden}
.nch{padding:1rem;background:linear-gradient(90deg,rgba(59,130,246,.1),transparent);border-bottom:1px solid var(--brd);font-weight:600;display:flex;align-items:center;gap:.5rem}
.ni{padding:.85rem 1rem;cursor:pointer;display:flex;align-items:center;gap:.75rem;transition:all .2s;border-left:3px solid transparent}
.ni:hover,.ni.act{border-left-color:var(--blu)}
.ni.act{background:rgba(59,130,246,.1)}
.ni .ic{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center}
.scores{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}
.sc{background:var(--bg2);border-radius:12px;padding:1.25rem;border:1px solid var(--brd);position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.sc.grn::before{background:var(--grn)}.sc.ylw::before{background:var(--ylw)}.sc.red::before{background:var(--red)}.sc.blu::before{background:var(--blu)}
.sl{font-size:.8rem;color:var(--fg2);text-transform:uppercase;letter-spacing:.05em}
.sv{font-size:2rem;font-weight:700;margin-top:.5rem}
.sv.grn{color:var(--grn)}.sv.ylw{color:var(--ylw)}.sv.red{color:var(--red)}.sv.blu{color:var(--blu)}
.st{font-size:.8rem;margin-top:.25rem;color:var(--fg2)}
.modt{background:var(--bg2);border-radius:12px;border:1px solid var(--brd);overflow:hidden}
.th{padding:1rem 1.25rem;background:linear-gradient(90deg,rgba(59,130,246,.1),transparent);border-bottom:1px solid var(--brd);font-weight:600;display:flex;justify-content:space-between;align-items:center}
.mr{display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 80px;padding:.875rem 1.25rem;border-bottom:1px solid rgba(71,85,105,.3);align-items:center;transition:background .2s;font-size:.85rem}
.mr:hover{background:rgba(59,130,246,.05)}
.mr:last-child{border-bottom:none}
.mn{display:flex;align-items:center;gap:.75rem}
.sd{width:10px;height:10px;border-radius:50%}
.sd.grn{background:var(--grn);box-shadow:0 0 8px var(--grn)}
.sd.ylw{background:var(--ylw);box-shadow:0 0 8px var(--ylw)}
.sd.red{background:var(--red);box-shadow:0 0 8px var(--red)}
.sb2{padding:.25rem .75rem;border-radius:20px;font-size:.75rem;font-weight:600;text-transform:uppercase}
.sb2.grn{background:rgba(34,197,94,.2);color:var(--grn)}
.sb2.ylw{background:rgba(234,179,8,.2);color:var(--ylw)}
.sb2.red{background:rgba(239,68,68,.2);color:var(--red)}
.hb{width:100%;height:6px;background:var(--bg);border-radius:3px;overflow:hidden}
.hbf{height:100%;border-radius:3px;transition:width .5s}
.gaps{background:var(--bg2);border-radius:12px;border:1px solid var(--brd);overflow:hidden}
.gf{padding:1rem 1.25rem;border-bottom:1px solid rgba(71,85,105,.3);display:grid;grid-template-columns:auto 1fr auto;gap:1rem;align-items:start;font-size:.85rem}
.gs{padding:.2rem .6rem;border-radius:4px;font-size:.7rem;font-weight:700;text-transform:uppercase}
.gs.crit{background:rgba(239,68,68,.2);color:var(--red)}
.gs.high{background:rgba(249,115,22,.2);color:#f97316}
.gs.med{background:rgba(234,179,8,.2);color:var(--ylw)}
.gs.low{background:rgba(59,130,246,.2);color:var(--blu)}
.gc{font-size:.75rem;padding:.15rem .5rem;background:var(--bg);border-radius:4px;color:var(--pur)}
.sb-right{display:flex;flex-direction:column;background:var(--bg2);border-radius:12px;border:1px solid var(--brd);overflow:hidden;height:calc(100vh - 120px);position:sticky;top:100px}
.ch{background:linear-gradient(135deg,var(--blu),var(--pur))}
.cm{flex:1;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;gap:.75rem;scroll-behavior:smooth}
.msg{max-width:88%;padding:.75rem 1rem;border-radius:12px;font-size:.88rem;line-height:1.5;animation:fi .3s;white-space:pre-wrap}
@keyframes fi{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.msg.u{background:linear-gradient(135deg,var(--blu),#2563eb);color:#fff;border-bottom-right-radius:4px;align-self:flex-end}
.msg.a{background:var(--bg3);border:1px solid var(--brd);border-bottom-left-radius:4px;align-self:flex-start;color:var(--fg)}
.msg h2,.msg h3{color:var(--blu);margin-bottom:.5rem;font-size:1rem}
.msg b,.msg strong{color:var(--grn)}
.msg code{background:var(--bg);padding:.1rem .3rem;border-radius:4px;font-size:.85em}
.cia{padding:1rem;border-top:1px solid var(--brd);display:flex;gap:.5rem}
.ci{flex:1;padding:.75rem 1rem;background:var(--bg);border:1px solid var(--brd);border-radius:8px;color:var(--fg);font-size:.9rem;outline:none}
.ci:focus{border-color:var(--blu);box-shadow:0 0 0 3px rgba(59,130,246,.2)}
.cs{width:42px;height:42px;background:linear-gradient(135deg,var(--blu),var(--pur));border:none;border-radius:8px;color:#fff;cursor:pointer;font-size:1.1rem;display:flex;align-items:center;justify-content:center}
.ty{display:none;align-self:flex-start;padding:.5rem 1rem;color:var(--fg2);font-size:.85rem}
.ty.act{display:flex}
.sp{position:fixed;top:80px;right:20px;background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:1rem;min-width:280px;box-shadow:0 10px 40px rgba(0,0,0,.5);display:none;z-index:200}
.sp.act{display:block}
.sbar{width:100%;height:4px;background:var(--bg);border-radius:2px;margin-top:.5rem;overflow:hidden}
.sbf{height:100%;background:linear-gradient(90deg,var(--blu),var(--pur));animation:sa 2s infinite}
@keyframes sa{0%{width:0%;margin-left:0}50%{width:50%;margin-left:25%}100%{width:0%;margin-left:100%}}
.ft{text-align:center;padding:1rem;color:var(--fg2);font-size:.8rem;border-top:1px solid var(--brd);margin-top:2rem}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--brd);border-radius:3px}
#tabs{display:flex;gap:2px;margin-bottom:1rem}
.tab{padding:.5rem 1rem;cursor:pointer;border-bottom:2px solid transparent;font-size:.85rem;color:var(--fg2);transition:all .2s}
.tab:hover{color:var(--fg)}
.tab.act{border-bottom-color:var(--blu);color:var(--blu);font-weight:600}
.tab-content{display:none}
.tab-content.act{display:block}
.fl{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.flc{background:var(--bg2);border-radius:12px;border:1px solid var(--brd);padding:1rem}
.flc h4{font-size:.85rem;color:var(--blu);margin-bottom:.5rem}
.fl-row{display:flex;align-items:center;gap:.5rem;padding:.5rem 0;font-size:.85rem;border-bottom:1px solid rgba(71,85,105,.2)}
.loc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.75rem}
.loc-card{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:.75rem;font-size:.82rem}
.loc-card h5{color:var(--blu);margin-bottom:.25rem}
.ht-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:.75rem}
.ht-card{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:.75rem;font-size:.82rem}
.ht-card h5{display:flex;justify-content:space-between;margin-bottom:.25rem}
.ht-score{font-weight:700}
.ht-score.grn{color:var(--grn)}.ht-score.ylw{color:var(--ylw)}.ht-score.red{color:var(--red)}
</style>
</head>
<body>
<header class="header">
<div class="logo-sec">
<div class="logo">IH</div>
<div class="tit"><h1>ERP IH System Launcher</h1><p>Diagnostic Dashboard v3.1 | Real-time Monitoring & AI Analysis</p></div>
</div>
<div class="act">
<button class="btn btn-sec" onclick="refreshData()">Refresh</button>
<button class="btn btn-pri" onclick="triggerScan()">Full System Scan</button>
</div>
</header>

<div class="sp" id="scanProgress">
<div style="display:flex;justify-content:space-between;align-items:center">
<span style="font-weight:600">Scanning...</span>
<span style="color:var(--fg2);font-size:.8rem" id="scanTimer">0s</span>
</div>
<div class="sbar"><div class="sbf"></div></div>
<div style="margin-top:.5rem;font-size:.8rem;color:var(--fg2)" id="scanStatus">Checking modules...</div>
</div>

<div class="main">
<aside class="sb-left">
<div class="ncard">
<div class="nch">Dashboard Views</div>
<div class="ni act" onclick="switchTab('overview')"><span class="ic">H</span><div><div style="font-weight:600">Overview</div><div style="font-size:.8rem;color:var(--fg2)">System health summary</div></div></div>
<div class="ni" onclick="switchTab('modules')"><span class="ic">M</span><div><div style="font-weight:600">Modules</div><div style="font-size:.8rem;color:var(--fg2)">Individual status</div></div></div>
<div class="ni" onclick="switchTab('gaps')"><span class="ic">G</span><div><div style="font-weight:600">Gap Analysis</div><div style="font-size:.8rem;color:var(--fg2)">Compliance scanner</div></div></div>
<div class="ni" onclick="switchTab('flow')"><span class="ic">F</span><div><div style="font-weight:600">Data Flow</div><div style="font-size:.8rem;color:var(--fg2)">Module data movement</div></div></div>
<div class="ni" onclick="switchTab('locations')"><span class="ic">L</span><div><div style="font-weight:600">Data Locations</div><div style="font-size:.8rem;color:var(--fg2)">Where data lives</div></div></div>
<div class="ni" onclick="switchTab('tables')"><span class="ic">T</span><div><div style="font-weight:600">Master Tables</div><div style="font-size:.8rem;color:var(--fg2)">Table health monitor</div></div></div>
</div>
<div class="ncard">
<div class="nch">Quick Actions</div>
<div class="ni" onclick="sendChat('health status')"><span class="ic">S</span><div>Check Health</div></div>
<div class="ni" onclick="sendChat('gap analysis')"><span class="ic">G</span><div>Run Gap Scan</div></div>
<div class="ni" onclick="sendChat('data flow')"><span class="ic">D</span><div>Data Flow Map</div></div>
<div class="ni" onclick="sendChat('data locations')"><span class="ic">L</span><div>Data Locations</div></div>
<div class="ni" onclick="sendChat('master tables')"><span class="ic">T</span><div>Master Tables</div></div>
</div>
</aside>

<main class="center-content" id="mainContent">
<div class="scores" id="scoreGrid">
<div class="sc grn"><div class="sl">System Health</div><div class="sv grn" id="healthScore">--</div><div class="st" id="healthTrend">Waiting for scan...</div></div>
<div class="sc blu"><div class="sl">Modules Online</div><div class="sv blu" id="modulesOnline">--</div><div class="st" id="modulesTrend">of -- total</div></div>
<div class="sc ylw"><div class="sl">Gap Findings</div><div class="sv ylw" id="gapCount">--</div><div class="st" id="gapTrend">ERP Builder v2.2</div></div>
<div class="sc blu"><div class="sl">Last Scan</div><div class="sv blu" id="lastScan">--</div><div class="st" id="scanDuration">--</div></div>
</div>

<div id="tabs">
<div class="tab act" onclick="switchTab('overview')">Overview</div>
<div class="tab" onclick="switchTab('modules')">Modules</div>
<div class="tab" onclick="switchTab('gaps')">Gap Analysis</div>
<div class="tab" onclick="switchTab('flow')">Data Flow</div>
<div class="tab" onclick="switchTab('locations')">Locations</div>
<div class="tab" onclick="switchTab('tables')">Master Tables</div>
</div>

<div id="tab-overview" class="tab-content act">
<div class="modt"><div class="th"><span>Module Status Monitor</span><span style="font-size:.8rem;color:var(--fg2)" id="lastUpdated">Never</span></div>
<div id="moduleTableBody"><div style="padding:2rem;text-align:center;color:var(--fg2)">Loading module data...</div></div></div>
<div class="gaps" id="gapSection" style="margin-top:1rem"><div class="th"><span>Gap Analysis Results</span><span style="font-size:.8rem;color:var(--fg2)" id="gapSummary">--</span></div>
<div id="gapFindingsBody"><div style="padding:2rem;text-align:center;color:var(--fg2)">Run a scan to see gap analysis</div></div></div>
</div>

<div id="tab-modules" class="tab-content"><div id="moduleDetail"><div style="padding:2rem;text-align:center;color:var(--fg2)">Select a module from the overview tab</div></div></div>
<div id="tab-gaps" class="tab-content"><div id="fullGapList"><div style="padding:2rem;text-align:center;color:var(--fg2)">Run a scan to see gap analysis</div></div></div>
<div id="tab-flow" class="tab-content"><div id="flowContent"><div style="padding:2rem;text-align:center;color:var(--fg2)">Run a scan to see data flows</div></div></div>
<div id="tab-locations" class="tab-content"><div id="locationContent"><div style="padding:2rem;text-align:center;color:var(--fg2)">Run a scan to see data locations</div></div></div>
<div id="tab-tables" class="tab-content"><div id="tableHealthContent"><div style="padding:2rem;text-align:center;color:var(--fg2)">Run a scan to see master table health</div></div></div>
</main>

<aside class="sb-right">
<div class="ch" style="padding:1rem;display:flex;align-items:center;gap:.75rem">
<div style="width:36px;height:36px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.25rem">AI</div>
<div><div style="font-weight:600">ERP-IH AI Assistant</div><div style="font-size:.75rem;opacity:.9">System Diagnostics</div></div>
<div style="margin-left:auto;font-size:.7rem;background:rgba(255,255,255,.2);padding:.2rem .5rem;border-radius:10px" id="wsStatus">Connecting</div>
</div>
<div class="cm" id="chatMessages">
<div class="msg a"><b>Welcome to ERP IH Launcher!</b><br><br>I can help you with:<br>
- <b>health</b> — System health report<br>
- <b>gap analysis</b> — Compliance scan<br>
- <b>data flow</b> — Module data movement<br>
- <b>data locations</b> — Where data lives<br>
- <b>master tables</b> — Table health monitor<br>
- <b>fix</b> — Repair instructions<br>
- <b>performance</b> — Speed analysis<br>
- <b>security</b> — Vulnerability check<br><br>
Type a message or use quick actions!</div>
</div>
<div class="ty" id="typingIndicator">AI is analyzing...</div>
<div class="cia">
<input class="ci" id="chatInput" placeholder="Ask about system health, gaps, fixes..." onkeypress="if(event.key==='Enter')sendChat()">
<button class="cs" onclick="sendChat()">S</button>
</div>
</aside>
</div>
<footer class="ft"><p>ERP IH Launcher v3.1 | FastAPI & WebSocket | Auto-scan every 30s</p></footer>

<script>
let ws=null,scanInterval=null;
function connectWS(){
 var p=window.location.protocol==='https:'?'wss:':'ws:';
 ws=new WebSocket(p+'//'+window.location.host+'/ws/chat');
 ws.onopen=function(){document.getElementById('wsStatus').textContent='Online';document.getElementById('wsStatus').style.color='#22c55e'};
 ws.onmessage=function(e){var d=JSON.parse(e.data);if(d.type==='message'){hideTyping();appendMsg('a',d.content)}};
 ws.onclose=function(){document.getElementById('wsStatus').textContent='Reconnecting';document.getElementById('wsStatus').style.color='#ef4444';setTimeout(connectWS,3000)};
}
function appendMsg(r,c){
 var el=document.getElementById('chatMessages');
 var m=document.createElement('div');m.className='msg '+(r==='u'?'u':'a');
 m.textContent=c;el.appendChild(m);el.scrollTop=el.scrollHeight;
}
function showTyping(){document.getElementById('typingIndicator').className='ty act'}
function hideTyping(){document.getElementById('typingIndicator').className='ty'}
function sendChat(msg){
 if(!msg){msg=document.getElementById('chatInput').value;document.getElementById('chatInput').value=''}
 if(!msg||!ws||ws.readyState!==1)return;
 appendMsg('u',msg);showTyping();ws.send(msg);
}
function switchTab(id){
 document.querySelectorAll('.tab').forEach(function(t){t.className='tab'});
 document.querySelectorAll('.tab-content').forEach(function(t){t.className='tab-content'});
 var t=document.querySelector('.tab[onclick*="'+id+'"]');if(t)t.className='tab act';
 var c=document.getElementById('tab-'+id);if(c)c.className='tab-content act';
}
function refreshData(){fetchModules();fetchGaps()}
function triggerScan(){
 document.getElementById('scanProgress').className='sp act';
 var t=0;document.getElementById('scanTimer').textContent='0s';
 var ti=setInterval(function(){t++;document.getElementById('scanTimer').textContent=t+'s'},1000);
 fetch('/api/v1/launcher/scan',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
  clearInterval(ti);document.getElementById('scanProgress').className='sp';
  updateScores(d.result);fetchModules();fetchGaps();
 }).catch(function(){clearInterval(ti);document.getElementById('scanProgress').className='sp'});
}
function updateScores(r){
 if(!r)return;
 document.getElementById('healthScore').textContent=r.overall_health_score+'%';
 var hc=document.getElementById('healthScore');hc.className='sv '+(r.overall_health_score>=70?'grn':r.overall_health_score>=40?'ylw':'red');
 document.getElementById('modulesOnline').textContent=r.modules_healthy;
 document.getElementById('modulesTrend').textContent='of '+r.modules_scanned+' total';
 document.getElementById('gapCount').textContent=r.gap_count||0;
 document.getElementById('lastScan').textContent=new Date(r.timestamp).toLocaleTimeString();
 document.getElementById('scanDuration').textContent=r.scan_duration_ms+'ms';
 if(r.recommendations&&r.recommendations.length){
  document.getElementById('healthTrend').textContent=r.recommendations[0];
 }
}
function fetchModules(){
 fetch('/api/v1/launcher/modules').then(function(r){return r.json()}).then(function(d){
  var mods=d.modules;var tbody=document.getElementById('moduleTableBody');
  var html='<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 80px;padding:.75rem 1.25rem;font-size:.8rem;color:var(--fg2);border-bottom:1px solid rgba(71,85,105,.3)"><span>Module</span><span>Status</span><span>Score</span><span>Port</span><span>Response</span><span>PID</span></div>';
  var order=['incentivehouse','bio_erp_core','event_core','database','redis','ih_sales','ih_bank_recon','or_module','scm_module'];
  order.forEach(function(k){
   var m=mods[k];if(!m)return;
   var sc=m.health_score;var cls=sc>=70?'grn':sc>=40?'ylw':'red';
   var st=m.status==='healthy'?'grn':m.status==='degraded'?'ylw':'red';
   html+='<div class="mr" onclick="showModule(\''+k+'\')"><div class="mn"><span class="sd '+st+'"></span>'+m.name+'</div><span class="sb2 '+st+'">'+m.status+'</span><span>'+sc+'%</span><span>'+(m.port||'--')+'</span><span>'+(m.response_time_ms?m.response_time_ms+'ms':'--')+'</span><span style="font-size:.75rem">'+(m.pid||'--')+'</span></div>';
  });
  if(order.length===0)html+='<div style="padding:1rem;text-align:center;color:var(--fg2)">No modules found</div>';
  tbody.innerHTML=html;
  document.getElementById('lastUpdated').textContent=new Date(d.timestamp).toLocaleString();
  // Update scores
  var h=0,t=0;for(var k in mods){t++;if(mods[k].status==='healthy')h++}
  if(t>0){document.getElementById('healthScore').textContent=Math.round(h/t*100)+'%';document.getElementById('modulesOnline').textContent=h;document.getElementById('modulesTrend').textContent='of '+t+' total'}
 }).catch(function(err){console.error('fetchModules error:',err)});
}
function fetchGaps(){
 fetch('/api/v1/launcher/gaps').then(function(r){return r.json()}).then(function(d){
  if(!d.findings||!d.findings.length){document.getElementById('gapFindingsBody').innerHTML='<div style="padding:2rem;text-align:center;color:var(--fg2)">No gaps found</div>';return}
  document.getElementById('gapSummary').textContent=d.total_findings+' findings';
  var html='';
  d.findings.forEach(function(f){
   var sc=f.severity==='critical'?'crit':f.severity==='high'?'high':f.severity==='medium'?'med':'low';
   html+='<div class="gf"><span class="gs '+sc+'">'+f.severity+'</span><div><b>'+f.module+'</b>: '+f.description+'<br><span style="font-size:.8rem;color:var(--fg2)">'+f.recommendation+'</span></div><span class="gc">'+(f.compliance||'')+'</span></div>';
  });
  document.getElementById('gapFindingsBody').innerHTML=html;
 }).catch(function(err){console.error('fetchGaps error:',err)});
}
function fetchFlows(){
 fetch('/api/v1/launcher/data-flows').then(function(r){return r.json()}).then(function(d){
  var c=document.getElementById('flowContent');
  if(!d.flows||!d.flows.length){c.innerHTML='<div style="padding:2rem;text-align:center;color:var(--fg2)">No flows detected</div>';return}
  var html='<div class="fl">';
  d.flows.forEach(function(f){
   var st=f.status==='active'?'grn':'ylw';
   html+='<div class="flc"><h4>'+f.source+' -> '+f.target+'</h4><div class="fl-row"><span class="sd '+st+'"></span> '+f.flow_type+'</div><div class="fl-row">Tables: '+f.tables.join(', ')+'</div><div class="fl-row">Status: <b>'+f.status+'</b></div></div>';
  });
  html+='</div>';c.innerHTML=html;
 }).catch(function(){});
}
function fetchLocations(){
 fetch('/api/v1/launcher/data-locations').then(function(r){return r.json()}).then(function(d){
  var c=document.getElementById('locationContent');
  if(!d.locations||!d.locations.length){c.innerHTML='<div style="padding:2rem;text-align:center;color:var(--fg2)">No locations found</div>';return}
  var html='<div class="loc-grid">';
  d.locations.forEach(function(l){
   var st=l.status==='active'||l.status==='synced'?'grn':'ylw';
   html+='<div class="loc-card"><h5>'+l.location_id+'</h5><div><span class="sd '+st+'"></span> '+l.location_type+' | '+l.path+'</div><div style="font-size:.75rem;color:var(--fg2)">'+(l.row_count?'Rows: '+l.row_count+' | ':'')+(l.size_bytes?'Size: '+l.size_bytes+' B | ':'')+'Updated: '+(l.last_updated?new Date(l.last_updated).toLocaleString():'N/A')+'</div></div>';
  });
  html+='</div>';c.innerHTML=html;
 }).catch(function(){});
}
function fetchTables(){
 fetch('/api/v1/launcher/master-tables').then(function(r){return r.json()}).then(function(d){
  var c=document.getElementById('tableHealthContent');
  if(!d.tables||!d.tables.length){c.innerHTML='<div style="padding:2rem;text-align:center;color:var(--fg2)">No tables found</div>';return}
  var html='<div class="ht-grid">';
  d.tables.forEach(function(t){
   var sc=t.health_score>=80?'grn':t.health_score>=50?'ylw':'red';
   var pk=t.has_primary_key?'Yes':'No';var ix=t.has_indexes?'Yes':'No';
   html+='<div class="ht-card"><h5><span>'+t.table_name+'</span><span class="ht-score '+sc+'">'+t.health_score+'/100</span></h5><div>Rows: '+t.row_count.toLocaleString()+' | Size: '+t.estimated_size+'</div><div>PK: '+pk+' | Indexes: '+ix+' | Sync: '+t.sync_status+'</div></div>';
  });
  html+='</div>';c.innerHTML=html;
 }).catch(function(){});
}
function showModule(id){
 document.querySelectorAll('.tab').forEach(function(t){t.className='tab'});
 document.querySelectorAll('.tab-content').forEach(function(t){t.className='tab-content'});
 document.getElementById('tab-modules').className='tab-content act';
 var t=document.querySelector('.tab[onclick*="modules"]');if(t)t.className='tab act';
 fetch('/api/v1/launcher/modules').then(function(r){return r.json()}).then(function(d){
  var m=d.modules[id];if(!m){document.getElementById('moduleDetail').innerHTML='<div style="padding:2rem;text-align:center;color:var(--fg2)">Module not found</div>';return}
  var st=m.status==='healthy'?'grn':m.status==='degraded'?'ylw':'red';
  var html='<div style="padding:1.25rem"><h2 style="color:var(--blu)">'+m.name+'</h2>';
  html+='<p><span class="sd '+st+'"></span> <b>'+m.status.toUpperCase()+'</b> | Score: '+m.health_score+'/100 | Port: '+(m.port||'N/A')+' | PID: '+(m.pid||'N/A')+'</p>';
  if(m.response_time_ms)html+='<p>Response: '+m.response_time_ms+'ms</p>';
  if(m.error_message)html+='<p style="color:var(--red)">Error: '+m.error_message+'</p>';
  if(Object.keys(m.file_integrity||{}).length){
   html+='<h3 style="color:var(--fg2);margin-top:1rem">File Integrity</h3>';var fi=m.file_integrity;
   for(var f in fi)html+='<div><span>'+(fi[f]?'OK':'MISSING')+'</span> '+f+'</div>';
  }
  if(Object.keys(m.db_table_counts||{}).length){
   html+='<h3 style="color:var(--fg2);margin-top:1rem">DB Tables</h3>';var dt=m.db_table_counts;
   for(var t in dt)html+='<div>'+t+': '+dt[t]+' rows</div>';
  }
  html+='</div>';document.getElementById('moduleDetail').innerHTML=html;
 }).catch(function(){});
}
// Auto-refresh
setInterval(function(){fetchModules()},15000);
setInterval(function(){fetchGaps()},30000);
// Init
connectWS();setTimeout(function(){triggerScan()},1000);
</script>
</body>
</html>
"""

@app.get("/")
async def serve_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/v1/launcher")
async def serve_dashboard_api():
    return HTMLResponse(content=DASHBOARD_HTML)

# ── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  ERP IH — System Launcher & Diagnostic Dashboard v3.1")
    print(f"  Port: 9002")
    print(f"  Base: {BASE_DIR}")
    print(f"  DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"{'='*60}\n")

    scanner.start_background_scanner()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9002,
        log_level="info"
    )
