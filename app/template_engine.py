from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from fastapi.responses import HTMLResponse

_template_dir: str = str(Path(__file__).parent / "templates")
_env: Environment | None = None


def get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(_template_dir), autoescape=True)
    return _env


def render_template(name: str, context: dict) -> HTMLResponse:
    template = get_env().get_template(name)
    html = template.render(**context)
    return HTMLResponse(html)
