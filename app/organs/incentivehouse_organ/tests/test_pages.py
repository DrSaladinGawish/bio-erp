"""
IHE-ERP v2.3 — Page route HTTP 200 tests.
Run: pytest tests/test_pages.py -v
Uses the `sync_client` and `app` fixtures from conftest.py.
"""
import pytest


# All page routes that must return 200
PAGE_ROUTES = [
    "/",
    "/evn",
    "/sal",
    "/pur",
    "/bnk",
    "/gl",
    "/documents",
    "/reports",
    "/neural",
    "/login",
    "/api/v1/incentivehouse/events/new",
    "/api/v1/incentivehouse/recon/form",
    "/api/v1/incentivehouse/purchasing",
    "/api/v1/incentivehouse/search",
]


@pytest.mark.parametrize("route", PAGE_ROUTES)
def test_page_returns_200(sync_client, route):
    """Every IHE-ERP page must return HTTP 200."""
    r = sync_client.get(route, follow_redirects=False)
    assert r.status_code == 200, f"{route} returned {r.status_code}"


def test_root_is_html(sync_client):
    r = sync_client.get("/")
    assert "text/html" in r.headers.get("content-type", "")


def test_login_has_username_field(sync_client):
    r = sync_client.get("/login")
    assert r.status_code == 200
    body = r.text.lower()
    assert "username" in body and "password" in body


def test_static_logo_assets():
    """The 4 brand images must exist on disk in either /static/img or /static/images
    (the running container serves them at /static/img)."""
    from pathlib import Path
    static_dir = Path(__file__).resolve().parent.parent / "static"
    candidates = [static_dir / "img", static_dir / "images"]
    expected = ["logos.jpg", "logosmal.jpg", "hader.jpg", "fotter.jpg"]
    # Find at least one of the candidate dirs that exists
    found_dirs = [d for d in candidates if d.exists()]
    assert found_dirs, f"Neither {candidates} exists"
    for name in expected:
        matches = [d / name for d in found_dirs if (d / name).exists()]
        assert matches, f"Missing asset: {name} not found in {[str(d) for d in found_dirs]}"
        for m in matches:
            assert m.stat().st_size > 0, f"Empty asset: {m}"
