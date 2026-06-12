"""
test_documents.py — Tests for Document Management System
"""

import pytest
from datetime import datetime
from uuid import UUID

pytestmark = pytest.mark.usefixtures("db_session")


def test_models_importable():
    from app.models.documents import SupportingDocument, DocumentModule

    assert SupportingDocument.__tablename__ == "supporting_documents"
    assert DocumentModule.__tablename__ == "document_modules"


def test_schemas_importable():
    from app.schemas.documents import (
        IngestRequest,
        DocumentOut,
    )

    assert IngestRequest.__name__ == "IngestRequest"
    assert DocumentOut.__name__ == "DocumentOut"


def test_service_importable():
    from app.services.document_service import DocumentService

    assert DocumentService.__name__ == "DocumentService"
    assert hasattr(DocumentService, "compute_sha256")
    assert hasattr(DocumentService, "ingest_module")
    assert hasattr(DocumentService, "verify_archive")


def test_router_importable():
    from app.routers.documents import router

    assert router.prefix == "/api/v1/documents"


def test_document_model_fields():
    from app.models.documents import SupportingDocument

    doc = SupportingDocument(
        module_name="Test",
        function_name="Test",
        transaction_table="test_table",
        transaction_id="123",
        archive_path="/tmp/test.pdf",
        file_hash_sha256="a" * 64,
        file_size_bytes=1024,
        file_name="test.pdf",
        file_ext="pdf",
    )
    assert doc.module_name == "Test"
    assert doc.status is None  # Column default applied at flush, not construction
    assert doc.file_ext == "pdf"


def test_document_module_fields():
    from app.models.documents import DocumentModule

    dm = DocumentModule(
        module_name="Bank",
        function_name="Statements",
        transaction_table="bnk_transactions",
        description="Monthly bank statements",
        filename_pattern="Bnk_{account}_{date}.pdf",
    )
    assert dm.module_name == "Bank"
    assert dm.transaction_table == "bnk_transactions"


def test_document_module_repr():
    from app.models.documents import DocumentModule

    dm = DocumentModule(
        module_name="Bank",
        function_name="Statements",
        transaction_table="bnk_transactions",
    )
    r = repr(dm)
    assert "Bank" in r and "Statements" in r


def test_supporting_document_repr():
    from app.models.documents import SupportingDocument

    doc = SupportingDocument(
        module_name="Bank",
        function_name="Statements",
        file_name="test.pdf",
        transaction_table="x",
        transaction_id="1",
        archive_path="/p",
        file_hash_sha256="a" * 64,
        file_size_bytes=1,
        file_ext="pdf",
    )
    r = repr(doc)
    assert "Bank" in r


def test_ingest_request_validates():
    from app.schemas.documents import IngestRequest

    req = IngestRequest(modules=["Bank"])
    assert req.usb_drive_letter == "D"
    assert req.auto_link is True
    assert req.copy_to_archive is True


def test_ingest_response_fields():
    from app.schemas.documents import IngestResponse, IngestResultItem

    resp = IngestResponse(
        total_files_found=10,
        ingested=8,
        linked=7,
        orphaned=1,
        errors=0,
        bytes_copied=50000,
        manifest=[
            IngestResultItem(
                file="Bank/test.pdf", status="linked", transaction_id="123"
            ),
        ],
    )
    assert resp.total_files_found == 10
    assert resp.linked == 7


def test_verify_request():
    from app.schemas.documents import VerifyRequest

    req = VerifyRequest(module_name="Bank")
    assert req.module_name == "Bank"


def test_link_request():
    from app.schemas.documents import LinkRequest

    uid = UUID("00000000-0000-0000-0000-000000000001")
    req = LinkRequest(document_id=uid, transaction_table="events", transaction_id="42")
    assert str(req.document_id) == "00000000-0000-0000-0000-000000000001"
    assert req.transaction_table == "events"


def test_document_out():
    from app.schemas.documents import DocumentOut

    doc = DocumentOut(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        module_name="Bank",
        function_name="Statements",
        transaction_table="bnk_transactions",
        transaction_id="42",
        archive_path="/tmp/test.pdf",
        file_hash_sha256="a" * 64,
        file_size_bytes=1024,
        file_name="test.pdf",
        file_ext="pdf",
        ingested_at=datetime.utcnow(),
        status="linked",
    )
    assert doc.module_name == "Bank"
    assert doc.status == "linked"


def test_document_list_response():
    from app.schemas.documents import DocumentListResponse

    resp = DocumentListResponse(total=0, items=[])
    assert resp.total == 0


def test_verify_result():
    from app.schemas.documents import VerifyResult

    vr = VerifyResult(total_checked=100, verified=90, modified=5, missing=3, errors=2)
    assert vr.total_checked == 100
    assert vr.verified == 90


def test_sha256_known_value():
    from app.services.document_service import DocumentService
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"hello world")
        fname = f.name
    try:
        h = DocumentService.compute_sha256(fname)
        assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    finally:
        os.unlink(fname)


@pytest.mark.skip(reason="Requires running server and DB")
def test_ingest_endpoint():
    """Integration test — requires server running and USB plugged in."""
    pass


@pytest.mark.skip(reason="Requires running server")
def test_verify_endpoint():
    """Integration test — requires server running."""
    pass
