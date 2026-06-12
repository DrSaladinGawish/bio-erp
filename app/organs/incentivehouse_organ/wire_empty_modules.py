"""
Wire-up for ALL 8 empty modules.
"""
from __future__ import annotations
import logging

logger = logging.getLogger("incentivehouse_organ.wire_empty_modules")

MODULES = [
    ("grn",      "Goods Receipt (GRN)",        "/api/v1/grn",          "grn_router"),
    ("cost",     "Cost Management",            "/api/v1/cost",         "cost_router"),
    ("event-budget", "Event Budget Tracking",  "/api/v1/event-budget", "event_budget_router"),
    ("budget",   "Budgeting & Forecasting",    "/api/v1/ih-budget",    "budget_router"),
    ("bsc",      "Balanced Scorecard",         "/api/v1/bsc",          "bsc_router"),
    ("bi",       "Business Intelligence",      "/api/v1/bi",           "bi_router"),
    ("approval", "Approval Workflow",          "/api/v1/workflow",     "approval_router"),
]


def wire(app, templates):
    try:
        from . import models_empty_modules  # noqa: F401
        logger.info("Empty-module models imported (%d tables)", len(models_empty_modules.EXTRA_PRODUCTION_MODELS))
    except Exception as exc:
        logger.warning("Could not import models_empty_modules: %s", exc)

    for mod_id, mod_name, prefix, router_file in MODULES:
        try:
            imp = __import__(f"app.organs.incentivehouse_organ.routers.{router_file}", fromlist=["router"])
            app.include_router(imp.router)
            logger.info("%s router mounted at %s", mod_name, prefix)
        except Exception as exc:
            logger.warning("%s router not mounted: %s", mod_name, exc)

    try:
        from fastapi.responses import HTMLResponse

        # Helper: add a page route, capturing the template name via default arg
        def _add_page(route: str, template: str, display: str):
            @app.get(route, response_class=HTMLResponse, include_in_schema=False)
            def _page(request, _t=template, _d=display):
                return templates.TemplateResponse(_t, {"request": request, "module_name": _d})

        for mod_id, mod_name, _ in MODULES:
            _add_page(f"/{mod_id}", f"{mod_id}.html", mod_name)
        logger.info("Empty-module pages wired: %s", ", ".join(f"/{m[0]}" for m in MODULES))
    except Exception as exc:
        logger.warning("Empty-module pages not wired: %s", exc)

    ev_ops_path = "/api/v1/event-ops"
    try:
        from .routers.event_ops import router as ev_ops_router
        app.include_router(ev_ops_router)
        logger.info("Event Ops router mounted at %s", ev_ops_path)
    except Exception as exc:
        logger.warning("Event Ops router not mounted: %s", exc)

    try:
        _add_page("/ops", "ops.html", "Event Operations")
    except Exception as exc:
        logger.warning("Ops page not wired: %s", exc)

    return app
