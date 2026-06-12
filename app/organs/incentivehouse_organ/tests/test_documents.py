"""Tests for the Document Management System API."""

import tempfile
import uuid
from pathlib import Path


def test_document_modules_seed(sync_client):
    r = sync_client.post("/api/v1/documents/modules/seed")
    assert r.status_code == 200
    body = r.json()
    assert "seeded" in body
    assert "message" in body


def test_document_modules_list(sync_client):
    sync_client.post("/api/v1/documents/modules/seed")
    r = sync_client.get("/api/v1/documents/modules")
    assert r.status_code == 200
    body = r.json()
    assert "modules" in body
    assert len(body["modules"]) > 0


def test_document_modules_seed_idempotent(sync_client):
    # First call seeds the modules; second call must be idempotent (seeded == 0)
    sync_client.post("/api/v1/documents/modules/seed")
    r2 = sync_client.post("/api/v1/documents/modules/seed")
    assert r2.json()["seeded"] == 0


def _clean_docs(sync_client):
    """Clean supporting_documents table for test isolation."""
    from app.organs.incentivehouse_organ.db import get_sync_engine

    eng = get_sync_engine()
    with eng.begin() as conn:
        conn.execute(__import__("sqlalchemy").text("DELETE FROM supporting_documents"))


def test_document_list_empty(sync_client):
    _clean_docs(sync_client)
    r = sync_client.get("/api/v1/documents/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_document_list_with_module_filter(sync_client):
    sync_client.post("/api/v1/documents/modules/seed")
    r = sync_client.get("/api/v1/documents/?module=Bank")
    assert r.status_code == 200


def test_document_get_not_found(sync_client):
    r = sync_client.get("/api/v1/documents/nonexistent-id")
    assert r.status_code == 404


def test_document_delete_not_found(sync_client):
    r = sync_client.delete("/api/v1/documents/nonexistent-id")
    assert r.status_code == 200  # soft-delete tries update, doesn't fail if missing


def test_document_ingest_no_usb(sync_client):
    """Ingest with non-existent USB path should return 400."""
    r = sync_client.post(
        "/api/v1/documents/ingest",
        json={
            "usb_drive_letter": "Z",
            "usb_base_path": "nonexistent\\path",
        },
    )
    assert r.status_code == 400


def test_document_ingest_basic(sync_client):
    """Ingest files from a temp directory, verify they are recorded."""
    _clean_docs(sync_client)
    sync_client.post("/api/v1/documents/modules/seed")
    tag = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp())
    usb_dir = tmp_dir / "USB_DRIVE"
    usb_dir.mkdir()
    (usb_dir / f"readme_{tag}.txt").write_text(f"hello world {tag}")
    (usb_dir / f"data_{tag}.csv").write_text(f"col1,col2\n1,{tag}")

    r = sync_client.post(
        "/api/v1/documents/ingest",
        json={
            "usb_drive_letter": "T",
            "usb_base_path": str(usb_dir),
            "compute_hash": True,
            "copy_to_archive": True,
            "auto_link": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_files_found"] == 2
    assert body["ingested"] == 2
    assert body["errors"] == 0

    # Verify records appear in listing
    r2 = sync_client.get("/api/v1/documents/")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 2


def test_document_ingest_duplicate_skipped(sync_client):
    """Ingesting the same file twice should skip the duplicate."""
    _clean_docs(sync_client)
    sync_client.post("/api/v1/documents/modules/seed")
    tag = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp())
    usb_dir = tmp_dir / "USB_DRIVE"
    usb_dir.mkdir()
    content = f"identical content {tag}"
    (usb_dir / "test.pdf").write_text(content)

    r1 = sync_client.post(
        "/api/v1/documents/ingest",
        json={
            "usb_drive_letter": "T",
            "usb_base_path": str(usb_dir),
        },
    )
    assert r1.status_code == 200
    assert r1.json()["ingested"] == 1

    r2 = sync_client.post(
        "/api/v1/documents/ingest",
        json={
            "usb_drive_letter": "T",
            "usb_base_path": str(usb_dir),
        },
    )
    assert r2.status_code == 200
    assert r2.json()["total_files_found"] == 1
    assert r2.json()["ingested"] == 0


def test_document_ingest_pattern_matching(sync_client):
    """Files matching known module patterns should be auto-categorised."""
    _clean_docs(sync_client)
    sync_client.post("/api/v1/documents/modules/seed")
    tag = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp())
    usb_dir = tmp_dir / "USB_DRIVE"
    usb_dir.mkdir()
    # Create a file matching the Sales/Invoices pattern: INV_{id}_*.pdf
    (usb_dir / f"INV_{tag}_test.pdf").write_text(f"dummy invoice {tag}")

    r = sync_client.post(
        "/api/v1/documents/ingest",
        json={
            "usb_drive_letter": "T",
            "usb_base_path": str(usb_dir),
        },
    )
    assert r.status_code == 200
    assert r.json()["ingested"] == 1

    r2 = sync_client.get("/api/v1/documents/")
    items = r2.json()["items"]
    inv_doc = next((d for d in items if d["file_name"] == f"INV_{tag}_test.pdf"), None)
    assert inv_doc is not None, f"INV_{tag}_test.pdf not found in {items}"
    assert inv_doc["module_name"] == "Sales"
    assert inv_doc["function_name"] == "Invoices"
    assert inv_doc["transaction_table"] == "sales_invoices"


def test_document_verify_empty(sync_client):
    r = sync_client.post("/api/v1/documents/verify", json={})
    assert r.status_code == 200
    body = r.json()
    assert "total_checked" in body


def test_document_module_out_shape(sync_client):
    sync_client.post("/api/v1/documents/modules/seed")
    r = sync_client.get("/api/v1/documents/modules")
    mod = r.json()["modules"][0]
    for key in ("module_name", "function_name", "transaction_table"):
        assert key in mod
