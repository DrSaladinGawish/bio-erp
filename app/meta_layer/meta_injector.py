import json, os, re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


META_STATIC_DIR = Path(__file__).parent.parent / "static" / "meta"
REGISTRY_PATH = Path(__file__).parent / "form_registry.json"


def get_form_registry() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _build_meta_rules(form_name: str, registry: dict) -> dict:
    forms = registry.get("forms", {})
    defn = forms.get(form_name)
    if not defn:
        return {}
    rules = {
        "form_name": form_name,
        "title": defn.get("title", ""),
        "auto_fill": {},
        "formulas": {},
        "validations": {},
        "conditions": {},
        "autosave": {"enabled": True, "interval_seconds": 30},
        "audit": {"enabled": True, "endpoint": "/api/meta/audit"},
    }
    for field in defn.get("fields", []):
        name = field["name"]
        if field.get("optionsEndpoint"):
            rules["auto_fill"][name] = {
                "trigger": "change",
                "fetch": field["optionsEndpoint"],
                "target_fields": {},
            }
    for rule in defn.get("autoCalcRules", []):
        rules["formulas"][rule["targetField"]] = rule["formula"]
    for field in defn.get("fields", []):
        name = field["name"]
        if field.get("required") or field.get("pattern") or field.get("min") is not None or field.get("max") is not None:
            v = {}
            if field.get("required"):
                v["required"] = True
            if field.get("pattern"):
                v["regex"] = field["pattern"]
                v["message"] = f"Must match pattern: {field['pattern']}"
            if field.get("min") is not None:
                v["min"] = field["min"]
            if field.get("max") is not None:
                v["max"] = field["max"]
            if field.get("maxLength"):
                v["max"] = field["maxLength"]
            rules["validations"][name] = v
    for field in defn.get("fields", []):
        if field.get("dependsOn"):
            dep = field["dependsOn"]
            values = json.dumps(dep["values"])
            rules["conditions"][field["name"]] = {"show_when": f"{dep['field']} in {values}"}
    return rules


class MetaLayerInjectorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._tags = None

    def _get_tags(self):
        if self._tags is not None:
            return self._tags
        meta_attrs = [
            "data-meta-config", "data-meta-vat",
            "data-meta-dashboard", "data-meta-list", "data-meta-nav",
            "data-meta-report", "data-meta-modules", "data-meta-documents",
        ]
        v2_scripts = [
            "meta_dashboard.js", "meta_list.js", "meta_nav.js",
            "meta_report.js", "meta_module_launcher.js", "meta_document.js",
        ]
        css_tag = b""
        css_path = META_STATIC_DIR / "meta_universal.css"
        if css_path.exists():
            css_tag = f'<link rel="stylesheet" href="/static/meta/meta_universal.css?v={int(os.path.getmtime(css_path))}">'.encode()
        core_js = b""
        for fname in ["meta_layer.js", "meta_vat.js"] + v2_scripts:
            fpath = META_STATIC_DIR / fname
            if fpath.exists():
                core_js += f'<script src="/static/meta/{fname}?v={int(os.path.getmtime(fpath))}"></script>'.encode()
        self._tags = (css_tag, core_js, meta_attrs)
        return self._tags

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return response
        if not hasattr(response, "body"):
            return response
        body = response.body
        css_tag, core_js, meta_attrs = self._get_tags()
        should_inject = any(attr.encode() in body for attr in meta_attrs) or b"<form" in body
        if not should_inject:
            return response
        if css_tag:
            body = body.replace(b"</head>", css_tag + b"</head>")
        if core_js:
            body = body.replace(b"</body>", core_js + b"</body>")
        return HTMLResponse(content=body, status_code=response.status_code, headers=dict(response.headers))


meta_router = APIRouter(prefix="/api/meta", tags=["meta"])


@meta_router.get("/config/{form_name}")
def get_meta_config(form_name: str):
    try:
        registry = get_form_registry()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Registry error: {e}")
    rules = _build_meta_rules(form_name, registry)
    if not rules:
        raise HTTPException(status_code=404, detail=f"No configuration found for form '{form_name}'")
    return JSONResponse(content=rules)


@meta_router.post("/audit")
def post_audit_log(data: dict):
    import datetime
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"meta_audit_{datetime.date.today().isoformat()}.jsonl"
    entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": data}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "logged"}


@meta_router.get("/draft/{form_name}")
def get_draft(form_name: str):
    return {"form_name": form_name, "draft": None}


@meta_router.post("/draft/{form_name}")
def save_draft(form_name: str, data: dict):
    import datetime
    draft_dir = Path(__file__).parent.parent / "drafts"
    draft_dir.mkdir(exist_ok=True)
    draft_file = draft_dir / f"{form_name}_{datetime.date.today().isoformat()}.json"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump({"form_name": form_name, "data": data, "updated_at": datetime.datetime.utcnow().isoformat()}, f)
    return {"status": "saved"}


@meta_router.get("/validate/unique")
def validate_unique(field: str, value: str, db_session=None):
    return {"field": field, "value": value, "unique": True}
