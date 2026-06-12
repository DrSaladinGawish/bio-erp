#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ERP IH — Launcher Dashboard Part 4 (P0)                                   ║
║  Features: Branding | AI Smart Window | Executive Summary                  ║
║  Port: 9003  |  v4.0.0                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import socket
import asyncio
import threading
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from contextlib import asynccontextmanager

# ── FastAPI ──────────────────────────────────────────────────────────────────
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Database ─────────────────────────────────────────────────────────────────
try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path("D:/ERP System/BIO_ERP") if sys.platform == "win32" else Path("/opt/bio_erp")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "bio_erp"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "connect_timeout": 5,
}

# ═════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class DataFlowNode:
    id: str
    name: str
    type: str
    module: str
    port: Optional[int]
    status: str
    last_activity: Optional[str]
    data_types: List[str]
    throughput_24h: Optional[int]
    error_rate: float
    health_score: int

@dataclass
class DataFlowEdge:
    id: str
    source: str
    target: str
    flow_type: str
    direction: str
    frequency: str
    record_count_24h: Optional[int]
    latency_ms: Optional[float]
    status: str
    last_sync: Optional[str]
    schema: List[str]

@dataclass
class DataLocation:
    entity_name: str
    entity_type: str
    primary_module: str
    primary_table: str
    primary_db: str
    replicas: List[Dict[str, str]]
    file_backups: List[str]
    api_endpoints: List[str]
    last_updated: Optional[str]
    row_count: Optional[int]
    size_mb: Optional[float]
    health_status: str
    staleness_hours: Optional[float]

@dataclass
class MasterTableHealth:
    table_name: str
    module: str
    database: str
    row_count: int
    row_count_trend: str
    last_insert: Optional[str]
    last_update: Optional[str]
    last_delete: Optional[str]
    days_since_update: Optional[float]
    staleness_threshold_hours: float
    is_stale: bool
    schema_hash: str
    schema_last_checked: str
    schema_drift_detected: bool
    drift_details: Optional[str]
    index_health: str
    index_fragmentation_pct: Optional[float]
    constraints_valid: bool
    orphan_count: int
    duplicate_count: int
    health_score: int
    recommendation: str

@dataclass
class DataFlowSnapshot:
    timestamp: str
    nodes: List[DataFlowNode]
    edges: List[DataFlowEdge]
    locations: List[DataLocation]
    master_tables: List[MasterTableHealth]
    overall_flow_health: int
    overall_data_health: int
    overall_master_health: int
    critical_alerts: List[str]

# ═════════════════════════════════════════════════════════════════════════════
# DATA FLOW ENGINE (from Part 3 — condensed)
# ═════════════════════════════════════════════════════════════════════════════

class DataFlowEngine:
    FLOW_TOPOLOGY = {
        "node_master_clients": {"name": "Master Clients", "type": "database_table", "module": "Bio-ERP Core", "port": 8000, "data_types": ["clients", "contacts", "billing_info"]},
        "node_master_vendors": {"name": "Master Vendors", "type": "database_table", "module": "Bio-ERP Core", "port": 8000, "data_types": ["vendors", "suppliers", "contracts"]},
        "node_master_items": {"name": "Master Items/Products", "type": "database_table", "module": "Bio-ERP Core", "port": 8000, "data_types": ["items", "products", "skus"]},
        "node_master_coa": {"name": "Chart of Accounts", "type": "database_table", "module": "Bio-ERP Core", "port": 8000, "data_types": ["accounts", "coa", "financial_codes"]},
        "node_master_staff": {"name": "Master Staff", "type": "database_table", "module": "Bio-ERP Core", "port": 8000, "data_types": ["employees", "staff", "roles"]},
        "node_eventcore_events": {"name": "EventCore Events", "type": "database_table", "module": "EventCore ERP", "port": 8001, "data_types": ["events", "event_details", "schedules"]},
        "node_eventcore_bookings": {"name": "EventCore Bookings", "type": "database_table", "module": "EventCore ERP", "port": 8001, "data_types": ["bookings", "reservations", "attendees"]},
        "node_ih_events": {"name": "IH Events", "type": "database_table", "module": "IncentiveHouse ERP", "port": 9001, "data_types": ["events", "event_lines", "client_events"]},
        "node_ih_sales": {"name": "IH Sales Line Items", "type": "database_table", "module": "IncentiveHouse ERP", "port": 9001, "data_types": ["sales", "line_items", "categories", "sub_categories"]},
        "node_ih_bank": {"name": "IH Bank Transactions", "type": "database_table", "module": "IncentiveHouse ERP", "port": 9001, "data_types": ["bank_transactions", "reconciliation", "ledger"]},
        "node_ih_clients": {"name": "IH Client Cache", "type": "database_table", "module": "IncentiveHouse ERP", "port": 9001, "data_types": ["clients", "client_events", "billing"]},
        "node_or_analysis": {"name": "OR Analysis Results", "type": "database_table", "module": "OR-ERP Module", "port": 8000, "data_types": ["lp_results", "eoq_results", "pert_results", "profit_analysis"]},
        "node_or_planning": {"name": "OR Planning Scenarios", "type": "file", "module": "OR-ERP Module", "port": 8000, "data_types": ["scenarios", "what_if", "recommendations"]},
        "node_scm_costing": {"name": "SCM Costing Data", "type": "database_table", "module": "SCM Module", "port": None, "data_types": ["cost_data", "variance", "budget"]},
        "node_scm_staging": {"name": "SCM Staging Tables", "type": "database_table", "module": "SCM Module", "port": None, "data_types": ["staging", "analysis", "temp_results"]},
        "node_excel_master": {"name": "Excel Master Data", "type": "file", "module": "External", "port": None, "data_types": ["coa", "items", "clients", "vendors", "staff"]},
        "node_excel_bank": {"name": "Excel Bank Transactions", "type": "file", "module": "External", "port": None, "data_types": ["bank_transactions", "narrations", "sub_ledger"]},
        "node_ai_ingest": {"name": "AI Ingest Pipeline", "type": "api", "module": "AI Layer", "port": None, "data_types": ["documents", "extracted_data", "classifications"]},
    }

    FLOW_EDGES = [
        {"id": "edge_1", "source": "node_master_clients", "target": "node_eventcore_events", "flow_type": "sync", "direction": "one_way", "frequency": "realtime", "schema": ["client_id", "client_name", "billing_info", "contact"]},
        {"id": "edge_2", "source": "node_master_items", "target": "node_eventcore_events", "flow_type": "sync", "direction": "one_way", "frequency": "realtime", "schema": ["item_id", "item_name", "category", "unit_price"]},
        {"id": "edge_3", "source": "node_eventcore_events", "target": "node_ih_events", "flow_type": "trigger", "direction": "one_way", "frequency": "on_demand", "schema": ["event_id", "event_name", "client_id", "start_date", "end_date", "status"]},
        {"id": "edge_4", "source": "node_eventcore_bookings", "target": "node_ih_sales", "flow_type": "batch", "direction": "one_way", "frequency": "hourly", "schema": ["booking_id", "event_id", "item_id", "quantity", "price"]},
        {"id": "edge_5", "source": "node_excel_bank", "target": "node_ih_bank", "flow_type": "batch", "direction": "one_way", "frequency": "daily", "schema": ["trnx_num", "trnx_type", "narration", "debit", "credit", "date", "account"]},
        {"id": "edge_6", "source": "node_excel_master", "target": "node_master_clients", "flow_type": "batch", "direction": "one_way", "frequency": "on_demand", "schema": ["client_id", "client_name", "category", "status"]},
        {"id": "edge_7", "source": "node_excel_master", "target": "node_master_items", "flow_type": "batch", "direction": "one_way", "frequency": "on_demand", "schema": ["item_id", "item_name", "category_id", "unit_cost", "unit_price"]},
        {"id": "edge_8", "source": "node_ih_events", "target": "node_or_analysis", "flow_type": "trigger", "direction": "one_way", "frequency": "on_demand", "schema": ["job_id", "requirements", "budget", "deadline", "resources"]},
        {"id": "edge_9", "source": "node_or_analysis", "target": "node_scm_staging", "flow_type": "async", "direction": "one_way", "frequency": "on_demand", "schema": ["scenario_id", "recommendation", "cost_projection", "timeline"]},
        {"id": "edge_10", "source": "node_ih_sales", "target": "node_scm_costing", "flow_type": "batch", "direction": "one_way", "frequency": "daily", "schema": ["sales_id", "category", "sub_category", "amount", "cost", "margin"]},
        {"id": "edge_11", "source": "node_ih_bank", "target": "node_ih_bank", "flow_type": "sync", "direction": "one_way", "frequency": "realtime", "schema": ["recon_status", "matched", "unmatched", "sub_ledger_code"]},
        {"id": "edge_12", "source": "node_ai_ingest", "target": "node_ih_events", "flow_type": "stream", "direction": "one_way", "frequency": "realtime", "schema": ["document_type", "extracted_fields", "confidence_score"]},
    ]

    def __init__(self):
        self._last_snapshot: Optional[DataFlowSnapshot] = None
        self._lock = threading.Lock()
        self._running = False

    def start_background_monitor(self):
        self._running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        return thread

    def _monitor_loop(self):
        while self._running:
            try:
                self.capture_snapshot()
            except Exception as e:
                print(f"[DATA FLOW ERROR] {e}")
            time.sleep(60)

    def capture_snapshot(self) -> DataFlowSnapshot:
        nodes = []
        for node_id, config in self.FLOW_TOPOLOGY.items():
            status = self._check_node_health(node_id, config)
            throughput = self._estimate_throughput(node_id)
            error_rate = self._estimate_error_rate(node_id)
            nodes.append(DataFlowNode(
                id=node_id, name=config["name"], type=config["type"], module=config["module"],
                port=config.get("port"), status=status, last_activity=self._get_last_activity(node_id),
                data_types=config["data_types"], throughput_24h=throughput,
                error_rate=error_rate, health_score=self._calc_node_health(status, error_rate)
            ))

        edges = []
        for edge_config in self.FLOW_EDGES:
            edge_status = self._check_edge_health(edge_config)
            latency = self._measure_edge_latency(edge_config)
            record_count = self._estimate_edge_volume(edge_config)
            edges.append(DataFlowEdge(
                id=edge_config["id"], source=edge_config["source"], target=edge_config["target"],
                flow_type=edge_config["flow_type"], direction=edge_config["direction"],
                frequency=edge_config["frequency"], record_count_24h=record_count,
                latency_ms=latency, status=edge_status,
                last_sync=self._get_last_sync(edge_config["id"]), schema=edge_config["schema"]
            ))

        locations = self._scan_data_locations()
        master_tables = self._check_master_tables()

        flow_health = int(sum(n.health_score for n in nodes) / max(len(nodes), 1))
        data_health = int(sum(l.health_status == "healthy" for l in locations) / max(len(locations), 1) * 100)
        master_health = int(sum(t.health_score for t in master_tables) / max(len(master_tables), 1))
        alerts = self._generate_flow_alerts(nodes, edges, locations, master_tables)

        snapshot = DataFlowSnapshot(
            timestamp=datetime.now().isoformat(), nodes=nodes, edges=edges,
            locations=locations, master_tables=master_tables,
            overall_flow_health=flow_health, overall_data_health=data_health,
            overall_master_health=master_health, critical_alerts=alerts
        )
        with self._lock:
            self._last_snapshot = snapshot
        return snapshot

    def _check_node_health(self, node_id: str, config: Dict) -> str:
        port = config.get("port")
        if port:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                return "active" if result == 0 else "offline"
            except:
                return "error"
        if config["type"] == "file":
            for p in [Path("D:/") / "Data_Base_Mtbls.xlsx", Path("D:/") / "Bnk_TRNX SOURCE.xlsx"]:
                if p.exists():
                    return "active"
            return "idle"
        return "active"

    def _estimate_throughput(self, node_id: str) -> Optional[int]:
        return {"node_ih_bank": 2501, "node_ih_sales": 190, "node_master_clients": 1751, "node_eventcore_events": 500}.get(node_id)

    def _estimate_error_rate(self, node_id: str) -> float:
        return 0.0

    def _get_last_activity(self, node_id: str) -> Optional[str]:
        return datetime.now().isoformat()

    def _calc_node_health(self, status: str, error_rate: float) -> int:
        score = {"active": 100, "idle": 70, "error": 30, "offline": 0}.get(status, 50)
        return max(0, min(100, score - int(error_rate * 10)))

    def _check_edge_health(self, edge_config: Dict) -> str:
        src = self._check_node_health(edge_config["source"], self.FLOW_TOPOLOGY.get(edge_config["source"], {}))
        tgt = self._check_node_health(edge_config["target"], self.FLOW_TOPOLOGY.get(edge_config["target"], {}))
        if src == "offline" or tgt == "offline":
            return "stalled"
        if src == "error" or tgt == "error":
            return "error"
        if src == "active" and tgt in ("active", "idle"):
            return "flowing"
        return "idle"

    def _measure_edge_latency(self, edge_config: Dict) -> Optional[float]:
        return {"sync": 50, "async": 200, "batch": 5000, "stream": 100, "trigger": 300}.get(edge_config["flow_type"], 100)

    def _estimate_edge_volume(self, edge_config: Dict) -> Optional[int]:
        return self._estimate_throughput(edge_config.get("source"))

    def _get_last_sync(self, edge_id: str) -> Optional[str]:
        return datetime.now().isoformat()

    def _scan_data_locations(self) -> List[DataLocation]:
        locations = []
        entity_map = [
            {"name": "clients", "type": "master", "primary": {"module": "Bio-ERP Core", "table": "clients", "db": "bio_erp"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "clients", "sync": "realtime"}, {"module": "EventCore ERP", "table": "client_cache", "sync": "hourly"}],
             "files": ["Data_Base_Mtbls.xlsx/Clnt_Mtbl"], "apis": ["/api/v1/clients", "/api/v1/clients/{id}"]},
            {"name": "events", "type": "transactional", "primary": {"module": "EventCore ERP", "table": "events", "db": "eventcore"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "events", "sync": "trigger"}, {"module": "Bio-ERP Core", "table": "event_sync", "sync": "realtime"}],
             "files": [], "apis": ["/api/v1/events", "/api/v1/events/{id}"]},
            {"name": "bank_transactions", "type": "transactional", "primary": {"module": "IncentiveHouse ERP", "table": "bnk_transactions", "db": "incentivehouse"},
             "replicas": [{"module": "Bio-ERP Core", "table": "transaction_bridge", "sync": "batch"}],
             "files": ["Bnk_TRNX SOURCE.xlsx", "Bnk_Trnx_Sub_Key.xlsx"], "apis": ["/api/v1/bank-recon/transactions", "/api/v1/bank-recon/reconcile"]},
            {"name": "sales_line_items", "type": "transactional", "primary": {"module": "IncentiveHouse ERP", "table": "sales_line_items", "db": "incentivehouse"},
             "replicas": [{"module": "SCM Module", "table": "scm_sales_staging", "sync": "daily"}],
             "files": [], "apis": ["/api/v1/sales/line-items", "/api/v1/jobs/{id}/line-items"]},
            {"name": "coa", "type": "reference", "primary": {"module": "Bio-ERP Core", "table": "coa_mtble", "db": "bio_erp"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "coa_cache", "sync": "on_demand"}],
             "files": ["Data_Base_Mtbls.xlsx/COA_Mtble", "Data_Base_Mtbls.xlsx/COA_Cat"], "apis": ["/api/v1/coa", "/api/v1/categories"]},
            {"name": "items", "type": "master", "primary": {"module": "Bio-ERP Core", "table": "einv_itm_mtble", "db": "bio_erp"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "items", "sync": "realtime"}, {"module": "EventCore ERP", "table": "item_cache", "sync": "hourly"}],
             "files": ["Data_Base_Mtbls.xlsx/EINV_Itm_Mtble", "Data_Base_Mtbls.xlsx/Itm_Cat"], "apis": ["/api/v1/items", "/api/v1/items/{id}"]},
            {"name": "staff", "type": "master", "primary": {"module": "Bio-ERP Core", "table": "stff_mtble", "db": "bio_erp"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "staff", "sync": "daily"}],
             "files": ["Data_Base_Mtbls.xlsx/Stff_Mtbl"], "apis": ["/api/v1/staff", "/api/v1/staff/{id}"]},
            {"name": "or_analysis_results", "type": "staging", "primary": {"module": "OR-ERP Module", "table": "or_results", "db": "bio_erp"},
             "replicas": [], "files": ["D:/Operational Research Module/scenarios/*.json"], "apis": ["/api/v1/or/lp/solve", "/api/v1/or/eoq/analyze", "/api/v1/or/pert/analyze"]},
            {"name": "scm_cost_analysis", "type": "staging", "primary": {"module": "SCM Module", "table": "scm_staging", "db": "bio_erp"},
             "replicas": [], "files": [], "apis": ["/api/v1/scm/costing", "/api/v1/scm/variance"]},
            {"name": "audit_trail", "type": "audit", "primary": {"module": "Bio-ERP Core", "table": "audit_trail", "db": "bio_erp"},
             "replicas": [{"module": "IncentiveHouse ERP", "table": "audit_log", "sync": "realtime"}],
             "files": [], "apis": ["/api/v1/audit", "/api/v1/audit/trail"]},
        ]
        for entity in entity_map:
            row_count, last_updated, size_mb = self._query_entity_stats(entity)
            staleness, is_stale = None, False
            if last_updated:
                try:
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    hours = (datetime.now() - dt).total_seconds() / 3600
                    staleness, is_stale = hours, hours > 24
                except:
                    pass
            health = "stale" if is_stale else ("empty" if row_count == 0 else "healthy")
            locations.append(DataLocation(
                entity_name=entity["name"], entity_type=entity["type"],
                primary_module=entity["primary"]["module"], primary_table=entity["primary"]["table"],
                primary_db=entity["primary"]["db"], replicas=entity["replicas"],
                file_backups=entity["files"], api_endpoints=entity["apis"],
                last_updated=last_updated, row_count=row_count, size_mb=size_mb,
                health_status=health, staleness_hours=staleness
            ))
        return locations

    def _query_entity_stats(self, entity: Dict) -> Tuple[Optional[int], Optional[str], Optional[float]]:
        if not DB_AVAILABLE:
            return None, None, None
        table_map = {"clients": "clients", "events": "events", "bank_transactions": "bnk_transactions",
                     "sales_line_items": "sales_line_items", "coa": "coa_mtble",
                     "items": "einv_itm_mtble", "staff": "stff_mtble",
                     "or_analysis_results": "or_results", "scm_cost_analysis": "scm_staging", "audit_trail": "audit_trail"}
        table = table_map.get(entity["name"])
        if not table:
            return None, None, None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            cursor.execute(f"SELECT MAX(GREATEST(COALESCE(updated_at, '1970-01-01'), COALESCE(created_at, '1970-01-01'))) FROM {table}")
            last_update = cursor.fetchone()[0]
            last_updated = last_update.isoformat() if last_update else None
            cursor.execute(f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))")
            size_str = cursor.fetchone()[0]
            size_mb = self._parse_size(size_str)
            cursor.close(); conn.close()
            return row_count, last_updated, size_mb
        except Exception as e:
            print(f"[DB QUERY ERROR] {entity['name']}: {e}")
            return None, None, None

    def _parse_size(self, size_str: str) -> Optional[float]:
        if not size_str:
            return None
        parts = size_str.split()
        if len(parts) != 2:
            return None
        val, unit = float(parts[0]), parts[1]
        multipliers = {"bytes": 1/1024/1024, "kB": 1/1024, "MB": 1, "GB": 1024, "TB": 1024*1024}
        return val * multipliers.get(unit, 1)

    def _check_master_tables(self) -> List[MasterTableHealth]:
        master_tables = []
        defs = [
            {"table": "clients", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "vendors", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "coa_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 168},
            {"table": "einv_itm_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "stff_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "pnr_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "sup_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "clnt_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "own_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 168},
            {"table": "bud_itm_mtble", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 24},
            {"table": "einv_trxmtbl", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 1},
            {"table": "bud_pur_trxtbl", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 1},
            {"table": "bud_sal_trxtbl", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 1},
            {"table": "events", "module": "IncentiveHouse ERP", "db": "incentivehouse", "threshold": 1},
            {"table": "sales_line_items", "module": "IncentiveHouse ERP", "db": "incentivehouse", "threshold": 1},
            {"table": "bnk_transactions", "module": "IncentiveHouse ERP", "db": "incentivehouse", "threshold": 1},
            {"table": "work_orders", "module": "IncentiveHouse ERP", "db": "incentivehouse", "threshold": 24},
            {"table": "purchase_orders", "module": "IncentiveHouse ERP", "db": "incentivehouse", "threshold": 24},
            {"table": "events", "module": "EventCore ERP", "db": "eventcore", "threshold": 1},
            {"table": "event_line_items", "module": "EventCore ERP", "db": "eventcore", "threshold": 1},
            {"table": "bookings", "module": "EventCore ERP", "db": "eventcore", "threshold": 1},
            {"table": "or_results", "module": "OR-ERP Module", "db": "bio_erp", "threshold": 168},
            {"table": "or_scenarios", "module": "OR-ERP Module", "db": "bio_erp", "threshold": 168},
            {"table": "scm_staging", "module": "SCM Module", "db": "bio_erp", "threshold": 24},
            {"table": "scm_costing", "module": "SCM Module", "db": "bio_erp", "threshold": 24},
            {"table": "audit_trail", "module": "Bio-ERP Core", "db": "bio_erp", "threshold": 1},
        ]
        for d in defs:
            master_tables.append(self._check_single_master_table(d))
        return master_tables

    def _check_single_master_table(self, table_def: Dict) -> MasterTableHealth:
        table, module, db, threshold = table_def["table"], table_def["module"], table_def["db"], table_def["threshold"]
        row_count, last_insert, last_update, last_delete = 0, None, None, None
        days_since, is_stale, schema_hash = None, True, "unknown"
        schema_drift, drift_details, index_health = False, None, "unknown"
        index_frag, constraints_valid, orphan_count = None, True, 0
        duplicate_count, health_score, recommendation = 0, 0, "Table not accessible"
        trend = "unknown"

        if DB_AVAILABLE:
            try:
                conn = psycopg2.connect(**{**DB_CONFIG, "database": db})
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE created_at >= NOW() - INTERVAL '24 hours'")
                new_24h = cursor.fetchone()[0]
                trend = "growing" if new_24h > 0 else ("stable" if row_count > 0 else "empty")
                for activity, col in [("insert", "created_at"), ("update", "updated_at")]:
                    try:
                        cursor.execute(f"SELECT MAX({col}) FROM {table}")
                        result = cursor.fetchone()[0]
                        if activity == "insert":
                            last_insert = result.isoformat() if result else None
                        else:
                            last_update = result.isoformat() if result else None
                    except:
                        pass
                if last_update:
                    try:
                        dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        days_since = (datetime.now() - dt).total_seconds() / 86400
                        is_stale = days_since > (threshold / 24)
                    except:
                        pass
                cursor.execute(f"SELECT md5(string_agg(column_name || data_type, ',' ORDER BY ordinal_position)) FROM information_schema.columns WHERE table_name = '{table}'")
                schema_hash_result = cursor.fetchone()
                schema_hash = schema_hash_result[0] if schema_hash_result else "unknown"
                cursor.execute(f"SELECT indexname, pg_size_pretty(pg_relation_size(indexrelid)), idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE relname = '{table}'")
                indexes = cursor.fetchall()
                if indexes:
                    idx_scans = sum(i[2] or 0 for i in indexes)
                    index_health = "optimal" if idx_scans > 0 else "unused"
                # FIX: COUNT(DISTINCT *) replaced with MD5 hash dedup
                try:
                    cursor.execute(f"SELECT COUNT(*) - COUNT(DISTINCT md5(CAST({table}.* AS TEXT))) FROM {table}")
                    dup_result = cursor.fetchone()
                    duplicate_count = dup_result[0] if dup_result else 0
                except Exception:
                    try:
                        cursor.execute(f"SELECT column_name FROM information_schema.key_column_usage WHERE table_name = '{table}' AND constraint_name LIKE '%%pkey%%'")
                        pk_cols = [r[0] for r in cursor.fetchall()]
                        if pk_cols:
                            pk_str = ', '.join(pk_cols)
                            cursor.execute(f"SELECT COUNT(*) - COUNT(DISTINCT ({pk_str})) FROM {table}")
                            dup_result = cursor.fetchone()
                            duplicate_count = dup_result[0] if dup_result else 0
                    except:
                        duplicate_count = 0
                cursor.close(); conn.close()
                health_score = 100
                if is_stale: health_score -= 30
                if row_count == 0 and table not in ["or_results", "or_scenarios"]: health_score -= 20
                if duplicate_count > 0: health_score -= 10
                if orphan_count > 0: health_score -= 15
                if index_health == "unused": health_score -= 5
                health_score = max(0, health_score)
                if is_stale:
                    recommendation = f"Table stale ({days_since:.1f} days). Trigger data refresh."
                elif duplicate_count > 0:
                    recommendation = f"Found {duplicate_count} duplicate rows. Run deduplication."
                elif orphan_count > 0:
                    recommendation = f"Found {orphan_count} orphan records. Check foreign keys."
                else:
                    recommendation = "Table healthy. No action needed."
            except Exception as e:
                recommendation = f"Error checking table: {str(e)[:100]}"
                health_score = 0

        return MasterTableHealth(
            table_name=table, module=module, database=db, row_count=row_count,
            row_count_trend=trend, last_insert=last_insert, last_update=last_update,
            last_delete=last_delete, days_since_update=days_since,
            staleness_threshold_hours=threshold, is_stale=is_stale,
            schema_hash=schema_hash, schema_last_checked=datetime.now().isoformat(),
            schema_drift_detected=schema_drift, drift_details=drift_details,
            index_health=index_health, index_fragmentation_pct=index_frag,
            constraints_valid=constraints_valid, orphan_count=orphan_count,
            duplicate_count=duplicate_count, health_score=health_score,
            recommendation=recommendation
        )

    def _generate_flow_alerts(self, nodes, edges, locations, master_tables) -> List[str]:
        alerts = []
        for s in [e for e in edges if e.status == "stalled"]:
            src_name = next((n.name for n in nodes if n.id == s.source), s.source)
            tgt_name = next((n.name for n in nodes if n.id == s.target), s.target)
            alerts.append(f"🚨 DATA FLOW STALLED: {src_name} → {tgt_name} ({s.flow_type})")
        for s in [l for l in locations if l.health_status == "stale"]:
            alerts.append(f"⚠️ STALE DATA: {s.entity_name} in {s.primary_module} ({s.staleness_hours:.1f}h old)")
        for u in [t for t in master_tables if t.health_score < 70]:
            alerts.append(f"🔴 MASTER TABLE: {u.table_name} ({u.module}) score {u.health_score}/100 — {u.recommendation[:60]}")
        for o in [n for n in nodes if n.status == "offline"]:
            alerts.append(f"❌ OFFLINE: {o.name} ({o.module}) on port {o.port}")
        return alerts[:20]

    def get_snapshot(self) -> Optional[DataFlowSnapshot]:
        with self._lock:
            return self._last_snapshot

    def get_flow_graph(self) -> Dict:
        snapshot = self.get_snapshot()
        if not snapshot:
            return {"error": "No snapshot available"}
        return {
            "nodes": [{"id": n.id, "label": n.name, "group": n.module, "type": n.type, "status": n.status,
                       "health": n.health_score, "throughput": n.throughput_24h,
                       "title": f"{n.name}<br>Module: {n.module}<br>Status: {n.status}<br>Health: {n.health_score}/100"}
                      for n in snapshot.nodes],
            "edges": [{"id": e.id, "from": e.source, "to": e.target, "label": e.flow_type, "status": e.status,
                       "latency": e.latency_ms, "volume": e.record_count_24h,
                       "title": f"{e.flow_type.upper()}<br>Status: {e.status}<br>Latency: {e.latency_ms}ms"}
                      for e in snapshot.edges]
        }

    def get_ai_insights(self) -> Dict:
        """Generate AI insights from current snapshot for the smart window."""
        snapshot = self.get_snapshot()
        if not snapshot:
            return {"summary": "No snapshot available. Run a scan first.", "insights": [], "actions": []}

        insights = []
        actions = []

        # Flow insights
        flowing = sum(1 for e in snapshot.edges if e.status == "flowing")
        stalled = sum(1 for e in snapshot.edges if e.status == "stalled")
        insights.append(f"{flowing} of {len(snapshot.edges)} data flows are active.")
        if stalled > 0:
            insights.append(f"{stalled} data flow(s) are stalled — check node connectivity.")
            actions.append("Check offline nodes in Data Flow tab")

        # Master table insights
        stale_tables = [t for t in snapshot.master_tables if t.is_stale]
        critical_tables = [t for t in snapshot.master_tables if t.health_score < 50]
        if stale_tables:
            insights.append(f"{len(stale_tables)} master table(s) need refresh.")
            actions.append("View stale tables in Master Tables tab")
        if critical_tables:
            insights.append(f"{len(critical_tables)} table(s) are in critical state.")
            actions.append("Run database health check")

        # Data location insights
        stale_data = [l for l in snapshot.locations if l.health_status == "stale"]
        if stale_data:
            insights.append(f"{len(stale_data)} data entity(ies) are stale.")

        overall = round((snapshot.overall_flow_health + snapshot.overall_data_health + snapshot.overall_master_health) / 3)
        summary = f"System health: {overall}%. {len(snapshot.critical_alerts)} alert(s) active."

        return {
            "summary": summary,
            "insights": insights,
            "actions": actions,
            "overall_health": overall,
            "alert_count": len(snapshot.critical_alerts),
            "timestamp": snapshot.timestamp
        }


# ═════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═════════════════════════════════════════════════════════════════════════════

flow_engine = DataFlowEngine()

async def _initial_snapshot():
    """Run initial snapshot in background to avoid blocking startup."""
    try:
        await asyncio.to_thread(flow_engine.capture_snapshot)
    except Exception as e:
        print(f"[INITIAL SNAPSHOT ERROR] {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    flow_engine.start_background_monitor()
    asyncio.create_task(_initial_snapshot())
    asyncio.create_task(_ws_broadcast_loop())
    yield
    flow_engine._running = False

app = FastAPI(
    title="ERP IH Launcher — Part 4",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── HTML Loading ─────────────────────────────────────────────────────────────

HERE = Path(__file__).parent.resolve()
DASHBOARD_HTML_PATH = HERE / "dashboard_part4.html"

def _load_dashboard_html() -> str:
    if DASHBOARD_HTML_PATH.exists():
        return DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
    # Fallback: try project root
    fallback = HERE.parent.parent.parent / "dashboard_part4.html"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return "<html><body><h1>dashboard_part4.html not found</h1><p>Place it next to this script.</p></body></html>"

# ── WebSocket ────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

async def _ws_broadcast_loop():
    while True:
        await asyncio.sleep(30)
        snapshot = flow_engine.get_snapshot()
        if snapshot:
            await manager.broadcast({
                "type": "snapshot",
                "payload": {
                    "timestamp": snapshot.timestamp,
                    "overall_flow_health": snapshot.overall_flow_health,
                    "overall_data_health": snapshot.overall_data_health,
                    "overall_master_health": snapshot.overall_master_health,
                    "critical_alerts": snapshot.critical_alerts,
                    "node_count": len(snapshot.nodes),
                    "edge_count": len(snapshot.edges),
                }
            })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root_dashboard():
    return HTMLResponse(content=_load_dashboard_html())

@app.get("/status")
async def launcher_status():
    snapshot = flow_engine.get_snapshot()
    return {
        "launcher": "ERP IH Launcher Part 4",
        "version": "4.0.0",
        "port": 9003,
        "status": "running",
        "websocket_clients": len(manager.active_connections),
        "last_snapshot": snapshot.timestamp if snapshot else None,
        "overall_health": {
            "flow": snapshot.overall_flow_health if snapshot else 0,
            "data": snapshot.overall_data_health if snapshot else 0,
            "master": snapshot.overall_master_health if snapshot else 0,
        }
    }

# ── Module Launcher API (P1) ──────────────────────────────────────────────────

MODULE_DEFS = [
    {"id": "bio_erp", "name": "Bio-ERP Core", "emoji": "🧠", "role": "Brain", "port": 8000, "url": "http://localhost:8000", "api_docs": "http://localhost:8000/docs"},
    {"id": "incentivehouse", "name": "IncentiveHouse ERP", "emoji": "🏠", "role": "Finance Hub", "port": 9001, "url": "http://localhost:9001", "api_docs": "http://localhost:9001/docs"},
    {"id": "part4", "name": "Data Flow Dashboard", "emoji": "🌊", "role": "Control Center", "port": 9003, "url": "http://localhost:9003", "api_docs": "http://localhost:9003/docs"},
    {"id": "eventcore", "name": "EventCore ERP", "emoji": "📅", "role": "Event Engine", "port": 8001, "url": "http://localhost:8001", "api_docs": "http://localhost:8001/docs"},
    {"id": "or_module", "name": "OR-ERP Module", "emoji": "⚙️", "role": "Optimization", "port": None, "url": "http://localhost:9001/api/v1/or", "api_docs": None},
    {"id": "scm_module", "name": "SCM Module", "emoji": "💰", "role": "Supply Chain", "port": None, "url": "http://localhost:9001/api/v1/scm", "api_docs": None},
    {"id": "ai_layer", "name": "AI Layer", "emoji": "🤖", "role": "Intelligence", "port": None, "url": None, "api_docs": None},
]

def _check_port(port: int, timeout: float = 1.5) -> bool:
    if port is None:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except:
        return False

@app.get("/modules")
async def get_modules_status():
    modules = []
    for m in MODULE_DEFS:
        online = _check_port(m["port"]) if m["port"] is not None else None
        status = "online" if online is True else ("offline" if online is False else "unknown")
        modules.append({
            "id": m["id"], "name": m["name"], "emoji": m["emoji"], "role": m["role"],
            "port": m["port"], "status": status, "health": 100 if status == "online" else (50 if status == "unknown" else 0),
            "url": m["url"], "api_docs": m["api_docs"],
            "last_seen": datetime.now().isoformat()
        })
    return {"modules": modules}

# ── Document Manager API (P1) ────────────────────────────────────────────────

KNOWN_FILES = [
    "D:/Data_Base_Mtbls.xlsx",
    "D:/Bnk_TRNX SOURCE.xlsx",
    "D:/Bnk_Trnx_Sub_Key.xlsx",
    "D:/IncentiveHouse_ERP/backups/archive.xlsx",
]

STAGING_DIR = Path("D:/IncentiveHouse_ERP/staging")

@app.get("/files")
async def get_files():
    files = []
    for path_str in KNOWN_FILES:
        path = Path(path_str)
        if path.exists():
            stat = path.stat()
            age_hours = (time.time() - stat.st_mtime) / 3600
            files.append({
                "name": path.name,
                "path": str(path),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "staleness_hours": round(age_hours, 1),
                "status": "healthy" if age_hours < 24 else ("stale" if age_hours < 168 else "archived")
            })
    if not files:
        # Fallback: scan D:\ for any .xlsx files
        try:
            for p in Path("D:/").glob("*.xlsx"):
                stat = p.stat()
                age_hours = (time.time() - stat.st_mtime) / 3600
                files.append({
                    "name": p.name, "path": str(p),
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "staleness_hours": round(age_hours, 1),
                    "status": "healthy" if age_hours < 24 else ("stale" if age_hours < 168 else "archived")
                })
        except:
            pass
    return {"files": files}

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = STAGING_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    stat = dest.stat()
    return {
        "filename": file.filename,
        "saved_to": str(dest),
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "uploaded_at": datetime.now().isoformat()
    }

# ── Flow API ─────────────────────────────────────────────────────────────────

@app.get("/flow/snapshot")
async def get_flow_snapshot():
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        return {"error": "No snapshot available"}
    return {
        "timestamp": snapshot.timestamp,
        "overall_flow_health": snapshot.overall_flow_health,
        "overall_data_health": snapshot.overall_data_health,
        "overall_master_health": snapshot.overall_master_health,
        "critical_alerts": snapshot.critical_alerts,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "location_count": len(snapshot.locations),
        "master_table_count": len(snapshot.master_tables),
    }

@app.post("/flow/snapshot")
async def post_flow_snapshot():
    snapshot = flow_engine.capture_snapshot()
    return {"message": "Snapshot captured", "timestamp": snapshot.timestamp,
            "node_count": len(snapshot.nodes), "edge_count": len(snapshot.edges)}

@app.get("/flow/graph")
async def get_flow_graph():
    return flow_engine.get_flow_graph()

@app.get("/flow/nodes")
async def get_flow_nodes():
    snapshot = flow_engine.get_snapshot()
    return {"nodes": [asdict(n) for n in snapshot.nodes]} if snapshot else {"nodes": []}

@app.get("/flow/edges")
async def get_flow_edges():
    snapshot = flow_engine.get_snapshot()
    return {"edges": [asdict(e) for e in snapshot.edges]} if snapshot else {"edges": []}

# ── Locations API ────────────────────────────────────────────────────────────

@app.get("/locations")
async def get_data_locations(entity_type: Optional[str] = Query(None), health_status: Optional[str] = Query(None)):
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        return {"locations": []}
    locations = snapshot.locations
    if entity_type:
        locations = [l for l in locations if l.entity_type == entity_type]
    if health_status:
        locations = [l for l in locations if l.health_status == health_status]
    return {"count": len(locations), "locations": [asdict(l) for l in locations]}

@app.get("/locations/{entity_name}")
async def get_data_location(entity_name: str):
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        raise HTTPException(404, "No snapshot")
    location = next((l for l in snapshot.locations if l.entity_name == entity_name), None)
    if not location:
        raise HTTPException(404, f"Entity {entity_name} not found")
    return asdict(location)

@app.get("/locations/map")
async def get_data_location_map():
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        return {"map": {}}
    by_module = defaultdict(list)
    for loc in snapshot.locations:
        by_module[loc.primary_module].append({
            "entity": loc.entity_name, "type": loc.entity_type, "table": loc.primary_table,
            "db": loc.primary_db, "rows": loc.row_count, "health": loc.health_status,
            "stale_hours": loc.staleness_hours, "replicas": len(loc.replicas),
            "files": len(loc.file_backups), "apis": len(loc.api_endpoints)
        })
    return {"map": dict(by_module), "total_entities": len(snapshot.locations)}

# ── Master Tables API ────────────────────────────────────────────────────────

@app.get("/master-tables")
async def get_master_tables(module: Optional[str] = Query(None), min_health: Optional[int] = Query(None, ge=0, le=100), stale_only: bool = Query(False)):
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        return {"tables": []}
    tables = snapshot.master_tables
    if module:
        tables = [t for t in tables if t.module == module]
    if min_health is not None:
        tables = [t for t in tables if t.health_score >= min_health]
    if stale_only:
        tables = [t for t in tables if t.is_stale]
    return {
        "count": len(tables),
        "healthy": sum(1 for t in tables if t.health_score >= 80),
        "degraded": sum(1 for t in tables if 50 <= t.health_score < 80),
        "critical": sum(1 for t in tables if t.health_score < 50),
        "tables": [asdict(t) for t in tables]
    }

@app.get("/master-tables/summary")
async def get_master_tables_summary():
    snapshot = flow_engine.get_snapshot()
    if not snapshot:
        return {"error": "No snapshot"}
    tables = snapshot.master_tables
    total_rows = sum(t.row_count for t in tables)
    return {
        "total_tables": len(tables), "total_rows": total_rows,
        "by_module": {
            module: {
                "count": len([t for t in tables if t.module == module]),
                "rows": sum(t.row_count for t in tables if t.module == module),
                "avg_health": round(sum(t.health_score for t in tables if t.module == module) / max(len([t for t in tables if t.module == module]), 1), 1)
            }
            for module in set(t.module for t in tables)
        },
        "stale_tables": [t.table_name for t in tables if t.is_stale],
        "critical_tables": [t.table_name for t in tables if t.health_score < 50],
        "overall_health": round(sum(t.health_score for t in tables) / max(len(tables), 1), 1)
    }

# ── NEW: AI Insights API ─────────────────────────────────────────────────────

@app.get("/ai/insights")
async def get_ai_insights():
    """Generate AI-powered insights from current system snapshot."""
    return flow_engine.get_ai_insights()


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
# SUB-APP FACTORY (for mounting into main BIO-ERP at /api/v1/launcher)
# ═════════════════════════════════════════════════════════════════════════════

def create_v4_app() -> FastAPI:
    """Factory function returning the Part 4 FastAPI sub-app.
    Use in main.py:
        from launcher_dashboard_v4_0 import create_v4_app
        app.mount("/api/v1/launcher", create_v4_app())
    """
    return app


if __name__ == "__main__":
    print("=" * 70)
    print("  ERP IH Launcher — Part 4: Presentation Cortex")
    print("  Port: 9003  |  Dashboard: http://localhost:9003")
    print("  API Docs: http://localhost:9003/docs")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=9003)
