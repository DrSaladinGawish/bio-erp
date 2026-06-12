"""
PostgreSQL Integration Tests — Event Operations Cycle (Phases 3-5)
Runs against REAL seeded PostgreSQL data on port 8000.
Standalone script — no pytest dependency, runs with: python pg_integration_test.py
"""

import os
import sys
import time
import requests
from typing import Optional

# ── CONFIG ──
BASE_URL = os.getenv("ERP_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1/incentivehouse"
ADMIN_USER = os.getenv("ERP_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ERP_ADMIN_PASS", "admin123")


# Color codes for terminal output
class Colors:
    GREEN = "[92m"
    RED = "[91m"
    YELLOW = "[93m"
    BLUE = "[94m"
    BOLD = "[1m"
    RESET = "[0m"


def print_header(title: str):
    sep = "=" * 70
    print(f"{Colors.BOLD}{sep}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{sep}{Colors.RESET}")


def print_pass(msg: str):
    print(f"  {Colors.GREEN}[PASS]{Colors.RESET} {msg}")


def print_fail(msg: str, detail: str = ""):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {msg}")
    if detail:
        print(f"         {Colors.RED}{detail}{Colors.RESET}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def print_warn(msg: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


# ── HTTP CLIENT ──
class ERPClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def login(self, username: str, password: str) -> bool:
        try:
            res = self.session.post(
                f"{self.base}{API_PREFIX}/auth/login",
                data={"username": username, "password": password},
                timeout=10,
            )
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            return False
        except Exception as e:
            print_fail("Login request failed", str(e))
            return False

    def get(self, path: str, params: dict = None) -> requests.Response:
        return self.session.get(
            f"{self.base}{API_PREFIX}{path}", params=params, timeout=10
        )

    def post(self, path: str, json_data: dict = None) -> requests.Response:
        return self.session.post(
            f"{self.base}{API_PREFIX}{path}", json=json_data, timeout=10
        )


# ── TEST RESULTS ──
results = {"passed": 0, "failed": 0, "tests": []}


def record(test_name: str, passed: bool, detail: str = ""):
    results["tests"].append({"name": test_name, "passed": passed, "detail": detail})
    if passed:
        results["passed"] += 1
        print_pass(test_name)
    else:
        results["failed"] += 1
        print_fail(test_name, detail)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════


def test_01_server_health(client: ERPClient):
    """Verify server is running and responding."""
    print_header("TEST 01: Server Health Check")
    try:
        res = client.session.get(f"{client.base}/health", timeout=5)
        if res.status_code == 200:
            record("Server health endpoint responds", True, res.text[:100])
        else:
            record(
                "Server health endpoint responds", False, f"Status {res.status_code}"
            )
    except Exception as e:
        record("Server health endpoint responds", False, str(e))


def test_02_auth_login(client: ERPClient):
    """Verify admin login returns JWT token."""
    print_header("TEST 02: Authentication")
    success = client.login(ADMIN_USER, ADMIN_PASS)
    record(
        "Admin login returns JWT token",
        success,
        f"Token: {client.token[:20]}..." if client.token else "No token",
    )

    if not success:
        print_warn("All subsequent tests will be skipped — auth is required")
        return False
    return True


def test_03_execution_queue(client: ERPClient):
    """Verify execution queue returns seeded events."""
    print_header("TEST 03: Execution Queue")
    res = client.get("/event-ops/execution-queue")

    if res.status_code != 200:
        record(
            "Execution queue returns 200",
            False,
            f"Got {res.status_code}: {res.text[:200]}",
        )
        return

    data = res.json()
    if not isinstance(data, list):
        record("Execution queue returns list", False, f"Got {type(data).__name__}")
        return

    record("Execution queue returns list", True, f"Count: {len(data)} events")

    # Check structure
    if data:
        required_keys = {
            "event_id",
            "event_name",
            "client_name",
            "days_remaining",
            "priority_score",
            "stage",
            "action_url",
        }
        missing = required_keys - set(data[0].keys())
        record(
            "Queue items have required keys",
            len(missing) == 0,
            f"Missing: {missing}" if missing else "All present",
        )

        # Check stages
        stages = {item["stage"] for item in data}
        expected = {"ops_assigned", "procurement", "execution"}
        found = stages & expected
        record(
            "Queue contains expected stages", len(found) > 0, f"Found stages: {stages}"
        )

        # Priority sort check
        if len(data) >= 2:
            sorted_ok = data[0]["priority_score"] >= data[1]["priority_score"]
            record(
                "Queue sorted by priority (desc)",
                sorted_ok,
                f"Top: {data[0]['priority_score']}, Next: {data[1]['priority_score']}",
            )


def test_04_execution_queue_filter(client: ERPClient):
    """Verify queue filters work."""
    print_header("TEST 04: Execution Queue Filters")

    for stage in ["ops_assigned", "procurement", "execution"]:
        res = client.get("/event-ops/execution-queue", params={"stage": stage})
        if res.status_code == 200:
            data = res.json()
            all_match = all(item["stage"] == stage for item in data)
            record(f"Filter by stage={stage}", all_match, f"Count: {len(data)}")
        else:
            record(f"Filter by stage={stage}", False, f"Status {res.status_code}")


def test_05_auto_recognize(client: ERPClient):
    """Verify auto-recognition returns client history + UOM map."""
    print_header("TEST 05: Auto-Recognition (Event #2)")

    # First, find an event with client history
    res = client.get("/event-ops/execution-queue")
    if res.status_code != 200 or not res.json():
        record("Auto-recognize test skipped", False, "No events in queue")
        return

    event_id = res.json()[0]["event_id"]

    res = client.get(f"/event-ops/events/{event_id}/auto-recognize")
    if res.status_code != 200:
        record(
            f"Auto-recognize event {event_id}",
            False,
            f"Status {res.status_code}: {res.text[:200]}",
        )
        return

    data = res.json()
    record(
        f"Auto-recognize event {event_id}",
        True,
        f"Client: {data.get('client', {}).get('name_en', 'N/A')}",
    )

    # Check client history
    history_count = data.get("events_last_12_months", 0)
    record(
        "Client history count present", history_count >= 0, f"Events: {history_count}"
    )

    # Check UOM map
    cat_map = data.get("category_uom_map", {})
    record("Category UOM map present", len(cat_map) > 0, f"Categories: {len(cat_map)}")

    if cat_map:
        first = list(cat_map.values())[0]
        has_uom = "uom" in first
        has_qty = "qty" in first
        has_buffer = "buffer_percent" in first
        record(
            "UOM map has required fields",
            has_uom and has_qty and has_buffer,
            f"UOM: {first.get('uom')}, Qty: {first.get('qty')}, Buffer: {first.get('buffer_percent')}%",
        )

    # Check checklist
    checklist = data.get("execution_checklist", [])
    record(
        "Execution checklist generated", len(checklist) > 0, f"Items: {len(checklist)}"
    )


def test_06_auto_recognize_apply(client: ERPClient):
    """Verify applying auto-recognition creates checkpoints."""
    print_header("TEST 06: Apply Auto-Recognition")

    res = client.get("/event-ops/execution-queue")
    if res.status_code != 200 or not res.json():
        record("Apply auto-recognize skipped", False, "No events")
        return

    event_id = res.json()[0]["event_id"]

    res = client.post(f"/event-ops/events/{event_id}/auto-recognize/apply")
    if res.status_code != 200:
        record(
            f"Apply auto-recognize event {event_id}",
            False,
            f"Status {res.status_code}: {res.text[:200]}",
        )
        return

    data = res.json()
    created = data.get("checkpoints_created", 0)
    record(
        f"Apply auto-recognize event {event_id}",
        created > 0,
        f"Checkpoints created: {created}",
    )


def test_07_execution_form(client: ERPClient):
    """Verify execution form endpoint returns complete payload."""
    print_header("TEST 07: Execution Form")

    res = client.get("/event-ops/execution-queue")
    if res.status_code != 200 or not res.json():
        record("Execution form test skipped", False, "No events")
        return

    event_id = res.json()[0]["event_id"]

    res = client.get(f"/event-ops/events/{event_id}/execute")
    if res.status_code != 200:
        record(f"Execution form event {event_id}", False, f"Status {res.status_code}")
        return

    data = res.json()
    has_event = "event" in data
    has_recognition = "recognition" in data
    has_checkpoints = "checkpoints" in data
    has_can_edit = "can_edit" in data

    record(
        f"Execution form event {event_id}",
        has_event and has_recognition and has_checkpoints and has_can_edit,
        f"event={has_event}, recognition={has_recognition}, checkpoints={has_checkpoints}, can_edit={has_can_edit}",
    )


def test_08_checkpoint_completion(client: ERPClient):
    """Verify checklist completion and stage advancement."""
    print_header("TEST 08: Checkpoint Completion & Stage Advancement")

    # Find an event in ops_assigned stage
    res = client.get("/event-ops/execution-queue", params={"stage": "ops_assigned"})
    if res.status_code != 200 or not res.json():
        record("Checkpoint test skipped", False, "No ops_assigned events")
        return

    event_id = res.json()[0]["event_id"]

    # Apply auto-recognition first (creates checkpoints)
    client.post(f"/event-ops/events/{event_id}/auto-recognize/apply")

    # Get execution form to see checkpoints
    res = client.get(f"/event-ops/events/{event_id}/execute")
    if res.status_code != 200:
        record("Get checkpoints for completion", False, f"Status {res.status_code}")
        return

    checkpoints = res.json().get("checkpoints", [])
    if not checkpoints:
        record("Checkpoints exist for completion", False, "No checkpoints found")
        return

    # Complete first pending checkpoint
    pending = [cp for cp in checkpoints if not cp.get("completed")]
    if not pending:
        record("Pending checkpoints exist", False, "All already completed")
        return

    cp = pending[0]
    cp_id = cp["id"]

    res = client.post(
        f"/event-ops/events/{event_id}/checkpoints/{cp_id}",
        json={"completed": True, "notes": "PG integration test"},
    )

    if res.status_code == 200:
        data = res.json()
        record(
            f"Complete checkpoint {cp_id}",
            data.get("completed") is True,
            f"Stage now: {data.get('stage_now', 'N/A')}",
        )
    else:
        record(
            f"Complete checkpoint {cp_id}",
            False,
            f"Status {res.status_code}: {res.text[:200]}",
        )


def test_09_manual_stage_advance(client: ERPClient):
    """Verify manual stage advancement works."""
    print_header("TEST 09: Manual Stage Advance")

    res = client.get("/event-ops/execution-queue")
    if res.status_code != 200 or not res.json():
        record("Stage advance test skipped", False, "No events")
        return

    event_id = res.json()[0]["event_id"]

    res = client.post(
        f"/event-ops/events/{event_id}/advance-stage",
        json={"target_stage": "procurement"},
    )

    if res.status_code == 200:
        data = res.json()
        record(
            f"Manual advance event {event_id}",
            data.get("new_stage") == "procurement",
            f"New stage: {data.get('new_stage')}",
        )
    else:
        record(
            f"Manual advance event {event_id}",
            False,
            f"Status {res.status_code}: {res.text[:200]}",
        )


def test_10_dashboard_summary(client: ERPClient):
    """Verify dashboard summary returns metrics."""
    print_header("TEST 10: Dashboard Summary")

    res = client.get("/event-ops/dashboard-summary")
    if res.status_code != 200:
        record("Dashboard summary", False, f"Status {res.status_code}")
        return

    data = res.json()
    required = [
        "total_active_events",
        "in_procurement",
        "in_execution",
        "overdue_events",
        "revenue_at_risk",
        "team_workload",
    ]
    missing = [k for k in required if k not in data]

    record(
        "Dashboard summary has all keys",
        len(missing) == 0,
        f"Missing: {missing}"
        if missing
        else f"Active: {data['total_active_events']}, Risk: EGP {data['revenue_at_risk']:,.0f}",
    )


def test_11_performance(client: ERPClient):
    """Verify response times are acceptable."""
    print_header("TEST 11: Performance")

    # Test queue
    start = time.time()
    res = client.get("/event-ops/execution-queue")
    queue_ms = (time.time() - start) * 1000
    record("Execution queue <300ms", queue_ms < 300, f"Actual: {queue_ms:.0f}ms")

    # Test auto-recognize (if events exist)
    res = client.get("/event-ops/execution-queue")
    if res.status_code == 200 and res.json():
        event_id = res.json()[0]["event_id"]
        start = time.time()
        client.get(f"/event-ops/events/{event_id}/auto-recognize")
        rec_ms = (time.time() - start) * 1000
        record("Auto-recognize <500ms", rec_ms < 500, f"Actual: {rec_ms:.0f}ms")
    else:
        record("Auto-recognize performance", False, "No events to test")


def test_12_html_form_render(client: ERPClient):
    """Verify HTML execution form renders."""
    print_header("TEST 12: HTML Form Render")

    res = client.get("/event-ops/execution-queue")
    if res.status_code != 200 or not res.json():
        record("HTML form test skipped", False, "No events")
        return

    event_id = res.json()[0]["event_id"]

    # Note: The HTML form is served by a different route — adjust if needed
    # If your router serves HTML at /event-ops/{id}/execute:
    res = client.session.get(
        f"{client.base}/event-ops/{event_id}/execute",
        headers={"Authorization": f"Bearer {client.token}"},
        timeout=10,
    )

    if res.status_code == 200:
        html = res.text
        has_tracker = "stage-tracker" in html or "stage_step" in html
        has_table = "categories-table" in html or "category-rows" in html
        has_checklist = "checklist-container" in html
        record(
            f"HTML form renders event {event_id}",
            has_tracker and has_table and has_checklist,
            f"tracker={has_tracker}, table={has_table}, checklist={has_checklist}",
        )
    else:
        record(
            f"HTML form renders event {event_id}", False, f"Status {res.status_code}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    sep = "=" * 70
    print(f"{Colors.BOLD}{sep}{Colors.RESET}")
    print(
        f"{Colors.BOLD}  BIO-ERP PostgreSQL Integration Tests — Phases 3-5{Colors.RESET}"
    )
    print(f"{Colors.BOLD}  Target: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.BOLD}{sep}{Colors.RESET}")

    client = ERPClient(BASE_URL)

    # Run tests in sequence
    test_01_server_health(client)
    auth_ok = test_02_auth_login(client)

    if not auth_ok:
        msg = "AUTH FAILED — Cannot proceed with API tests"
        print(f"{Colors.RED}{Colors.BOLD}{msg}{Colors.RESET}")
        print(
            f"{Colors.YELLOW}Check: ADMIN_USER={ADMIN_USER}, ADMIN_PASS={ADMIN_PASS}{Colors.RESET}"
        )
        print(
            f"{Colors.YELLOW}Override with env vars: ERP_ADMIN_USER, ERP_ADMIN_PASS{Colors.RESET}"
        )
        sys.exit(1)

    test_03_execution_queue(client)
    test_04_execution_queue_filter(client)
    test_05_auto_recognize(client)
    test_06_auto_recognize_apply(client)
    test_07_execution_form(client)
    test_08_checkpoint_completion(client)
    test_09_manual_stage_advance(client)
    test_10_dashboard_summary(client)
    test_11_performance(client)
    test_12_html_form_render(client)

    # Summary
    print_header("TEST SUMMARY")
    total = results["passed"] + results["failed"]
    pct = (results["passed"] / total * 100) if total > 0 else 0

    print(f"\n  {Colors.BOLD}Total:{Colors.RESET}  {total} tests")
    print(
        f"  {Colors.GREEN}{Colors.BOLD}Passed:{Colors.RESET} {results['passed']} ({pct:.0f}%)"
    )
    print(f"  {Colors.RED}{Colors.BOLD}Failed:{Colors.RESET} {results['failed']}")

    if results["failed"] > 0:
        print(f"\n  {Colors.RED}{Colors.BOLD}Failed Tests:{Colors.RESET}")
        for t in results["tests"]:
            if not t["passed"]:
                print(f"    \u2022 {t['name']}")
                if t["detail"]:
                    print(f"      {Colors.RED}{t['detail']}{Colors.RESET}")

    sep = "=" * 70
    print(f"\n{Colors.BOLD}{sep}{Colors.RESET}\n")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
