from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    source_id: Optional[str] = None
    format: str = Field(default="xlsx", pattern=r"^(xlsx|pdf|csv)$")
    data: Optional[dict[str, Any]] = None
    template_name: Optional[str] = None


class ReportResponse(BaseModel):
    filename: str
    format: str
    path: str
    report_type: str
    source_id: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class ReportType:
    OR_ANALYSIS = "or_analysis"
    SCM_COST = "scm_cost"
    SUSTAINABILITY = "sustainability"
    INVENTORY = "inventory"
    PERT_CHART = "pert_chart"
    EXECUTIVE_SUMMARY = "executive_summary"
