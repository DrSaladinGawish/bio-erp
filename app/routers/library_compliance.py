"""
Library Compliance Checker (LCC) Router
Part of ERP Builder Agent (EBA) v1.0
BIO-ERP — FastAPI Bridge
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database import get_db
from app.models.library_compliance import LibraryComplianceScan, LibraryWhitelist

router = APIRouter(prefix="/library", tags=["Library Compliance"])


# ─────────────────────────────── SCHEMAS ───────────────────────────────

class ScanTriggerRequest(BaseModel):
    scope: List[str] = Field(default=["python"], description="Scopes: python, nodejs, docker, system")
    severity: str = Field(default="all", description="Filter: all, critical, high, medium, low")

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str
    estimated_duration: str

class LibraryStatusResponse(BaseModel):
    last_scan_id: Optional[str]
    last_scan_time: Optional[datetime]
    compliance_score: Optional[float]
    grade: Optional[str]
    summary: Dict[str, Any]
    is_scanning: bool = False

class WhitelistEntry(BaseModel):
    package_name: str
    version_constraint: str = ">=0.0.0"
    reason: str
    expires_at: Optional[datetime] = None

class WhitelistResponse(BaseModel):
    id: int
    package_name: str
    version_constraint: str
    reason: str
    added_by: str
    added_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

class ReportResponse(BaseModel):
    scan_id: str
    timestamp: datetime
    scope: List[str]
    total_packages: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    pass_count: int
    compliance_score: float
    grade: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    status: str


# ─────────────────────────────── HELPERS ───────────────────────────────

def calculate_grade(score: float) -> str:
    if score >= 95: return "A+"
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 50: return "C"
    return "F"

def generate_scan_id() -> str:
    return f"lcc-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


# ─────────────────────────────── ENDPOINTS ───────────────────────────────

@router.get("/status", response_model=LibraryStatusResponse)
async def get_library_status(db: AsyncSession = Depends(get_db)):
    """Get latest library compliance status and score."""
    result = await db.execute(
        select(LibraryComplianceScan).order_by(LibraryComplianceScan.timestamp.desc())
    )
    last_scan = result.scalar_one_or_none()

    if not last_scan:
        return LibraryStatusResponse(
            last_scan_id=None,
            last_scan_time=None,
            compliance_score=None,
            grade=None,
            summary={},
            is_scanning=False
        )

    return LibraryStatusResponse(
        last_scan_id=last_scan.scan_id,
        last_scan_time=last_scan.timestamp,
        compliance_score=last_scan.compliance_score,
        grade=calculate_grade(last_scan.compliance_score),
        summary={
            "total": last_scan.total_packages,
            "critical": last_scan.critical_count,
            "high": last_scan.high_count,
            "medium": last_scan.medium_count,
            "low": last_scan.low_count,
            "pass": last_scan.pass_count
        },
        is_scanning=False
    )


@router.post("/scan", response_model=ScanResponse)
async def trigger_library_scan(
    request: ScanTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger a manual library compliance scan."""
    scan_id = generate_scan_id()

    # In production, this would queue a background job
    # For now, we acknowledge and log the trigger

    return ScanResponse(
        scan_id=scan_id,
        status="queued",
        message=f"Library compliance scan queued for scopes: {', '.join(request.scope)}",
        estimated_duration="2-5 minutes"
    )


@router.get("/report/{scan_id}", response_model=ReportResponse)
async def get_library_report(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed report for a specific scan."""
    result = await db.execute(
        select(LibraryComplianceScan).where(LibraryComplianceScan.scan_id == scan_id)
    )
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return ReportResponse(
        scan_id=scan.scan_id,
        timestamp=scan.timestamp,
        scope=scan.scope,
        total_packages=scan.total_packages,
        critical_count=scan.critical_count,
        high_count=scan.high_count,
        medium_count=scan.medium_count,
        low_count=scan.low_count,
        pass_count=scan.pass_count,
        compliance_score=scan.compliance_score,
        grade=calculate_grade(scan.compliance_score),
        findings=scan.findings,
        recommendations=scan.recommendations,
        status=scan.status
    )


@router.post("/whitelist", response_model=WhitelistResponse)
async def add_to_whitelist(
    entry: WhitelistEntry,
    db: AsyncSession = Depends(get_db),
    current_user: str = "admin"  # Replace with actual auth dependency
):
    """Add a package to the compliance whitelist (admin only)."""
    db_entry = LibraryWhitelist(
        package_name=entry.package_name,
        version_constraint=entry.version_constraint,
        reason=entry.reason,
        added_by=current_user,
        expires_at=entry.expires_at or (datetime.utcnow() + timedelta(days=365)),
        is_active=True
    )
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    return WhitelistResponse(
        id=db_entry.id,
        package_name=db_entry.package_name,
        version_constraint=db_entry.version_constraint,
        reason=db_entry.reason,
        added_by=db_entry.added_by,
        added_at=db_entry.added_at,
        expires_at=db_entry.expires_at,
        is_active=db_entry.is_active
    )


@router.get("/whitelist", response_model=List[WhitelistResponse])
async def list_whitelist(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all whitelisted packages."""
    stmt = select(LibraryWhitelist)
    if active_only:
        stmt = stmt.where(LibraryWhitelist.is_active == True)
    stmt = stmt.order_by(LibraryWhitelist.added_at.desc())
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [
        WhitelistResponse(
            id=e.id,
            package_name=e.package_name,
            version_constraint=e.version_constraint,
            reason=e.reason,
            added_by=e.added_by,
            added_at=e.added_at,
            expires_at=e.expires_at,
            is_active=e.is_active
        )
        for e in entries
    ]


@router.delete("/whitelist/{entry_id}")
async def remove_from_whitelist(
    entry_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a package from the whitelist."""
    result = await db.execute(
        select(LibraryWhitelist).where(LibraryWhitelist.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")

    entry.is_active = False
    await db.commit()

    return {"status": "removed", "entry_id": entry_id, "package": entry.package_name}
