# ═════════════════════════════════════════════════════════════════════════════
# PART 3 TAIL — Close DASHBOARD_HTML + JS + Routes + Entry Point
# Append this after the existing DASHBOARD_HTML = """ ... content
# ═════════════════════════════════════════════════════════════════════════════

# ── Replace the DASHBOARD_HTML assignment approach ──────────────────────────
# Instead of DASHBOARD_HTML = """...""" (which risks triple-quote conflicts),
# write the HTML as a separate file and read it:

import pathlib

_HERE = pathlib.Path(__file__).parent
_DASHBOARD_HTML_PATH = _HERE / "dashboard_part3.html"

def _load_dashboard_html() -> str:
    """Load dashboard HTML from the companion file."""
    try:
        return _DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "<html><body><h1>Dashboard HTML not found</h1><p>Expected at: {}</p></body></html>".format(_DASHBOARD_HTML_PATH)

DASHBOARD_HTML = _load_dashboard_html()

# ── Root Route ───────────────────────────────────────────────────────────────

@app.get("/")
async def get_dashboard():
    """Serve the Part 3 Data Flow & Health Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/v1/launcher")
async def get_launcher():
    """Alias for the dashboard (compatibility with launcher)."""
    return HTMLResponse(content=DASHBOARD_HTML)


# ═════════════════════════════════════════════════════════════════════════════
# WEBSOCKET — Real-time updates
# ═════════════════════════════════════════════════════════════════════════════

connected_websockets: List[WebSocket] = []

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            # Wait for client message (ping / trigger)
            data = await websocket.receive_text()
            if data == "ping":
                snapshot = flow_engine.get_snapshot()
                if snapshot:
                    await websocket.send_json({
                        "type": "snapshot_summary",
                        "timestamp": snapshot.timestamp,
                        "overall_flow_health": snapshot.overall_flow_health,
                        "overall_data_health": snapshot.overall_data_health,
                        "overall_master_health": snapshot.overall_master_health,
                        "critical_alerts": snapshot.critical_alerts,
                    })
            elif data == "trigger_scan":
                snapshot = flow_engine.capture_snapshot()
                await websocket.send_json({
                    "type": "scan_complete",
                    "timestamp": snapshot.timestamp,
                    "node_count": len(snapshot.nodes),
                    "edge_count": len(snapshot.edges),
                })
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


# ═════════════════════════════════════════════════════════════════════════════
# FIX: PostgreSQL COUNT(*) - COUNT(DISTINCT *) is invalid
# ═════════════════════════════════════════════════════════════════════════════
#
# In _check_single_master_table(), replace the buggy line:
#   cursor.execute(f"SELECT COUNT(*) - COUNT(DISTINCT *) FROM {table}")
# with a proper column-aware dedup query.

# The fix (to be applied in the existing method):
_CHECK_DUPLICATES_FIX = """
-- Instead of: COUNT(*) - COUNT(DISTINCT *)
-- Use a subquery to find true duplicates:
SELECT COUNT(*) - COUNT(DISTINCT row_id)
FROM (
    SELECT md5((t::text)::bytea) AS row_id
    FROM {table} t
) sub
"""

# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    PORT = 9003
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   ERP IH — Data Flow & Master Health Dashboard v3.1        ║")
    print(f"║   Port: {PORT}                                               ║")
    print("║   Endpoints:                                                 ║")
    print("║     • /               — Dashboard UI                        ║")
    print("║     • /api/v1/flow/*  — Data Flow Visualization            ║")
    print("║     • /api/v1/locations/* — Data Location Map              ║")
    print("║     • /api/v1/master-tables/* — Master Table Health        ║")
    print("║     • /ws/live        — WebSocket live updates             ║")
    print("║   Docs: http://127.0.0.1:{}/docs                            ║".format(PORT))
    print("╚══════════════════════════════════════════════════════════════╝")
    
    uvicorn.run(
        "launcher_dashboard_v3_1:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
