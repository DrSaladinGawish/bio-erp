from __future__ import annotations

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.organs.ebuild_organ import schemas
from app.organs.ebuild_organ.services import (
    ProfileService,
    CycleService,
    ModuleService,
    BuildService,
    CompanyService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ebuild"])


def get_db():
    db = get_sync_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/profiles", response_model=schemas.PaginatedResponse[schemas.EbuildActivityProfileResponse])
def list_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    total, items = ProfileService.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return {"total": total, "page": skip // limit + 1 if limit > 0 else 1, "page_size": limit, "items": items}


@router.get("/profiles/{profile_code}", response_model=schemas.ApiResponse[schemas.EbuildActivityProfileResponse])
def get_profile(profile_code: str, db: Session = Depends(get_db)):
    profile = ProfileService.get_by_code(db, profile_code)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_code}' not found")
    return {"success": True, "data": profile}


@router.post("/profiles", response_model=schemas.ApiResponse[schemas.EbuildActivityProfileResponse], status_code=201)
def create_profile(data: schemas.EbuildActivityProfileCreate, db: Session = Depends(get_db)):
    existing = ProfileService.get_by_code(db, data.profile_code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Profile '{data.profile_code}' already exists")
    profile = ProfileService.create(db, data.model_dump())
    return {"success": True, "data": profile}


@router.patch("/profiles/{profile_code}", response_model=schemas.ApiResponse[schemas.EbuildActivityProfileResponse])
def update_profile(profile_code: str, data: schemas.EbuildActivityProfileUpdate, db: Session = Depends(get_db)):
    profile = ProfileService.get_by_code(db, profile_code)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_code}' not found")
    profile = ProfileService.update(db, profile, data.model_dump(exclude_unset=True))
    return {"success": True, "data": profile}


@router.delete("/profiles/{profile_code}", response_model=schemas.ApiResponse)
def delete_profile(profile_code: str, db: Session = Depends(get_db)):
    profile = ProfileService.get_by_code(db, profile_code)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_code}' not found")
    ProfileService.delete(db, profile)
    return {"success": True, "message": f"Profile '{profile_code}' deleted"}


@router.get("/profiles/{profile_code}/plan", response_model=schemas.ApiResponse[schemas.BuildPlanResponse])
def get_build_plan(profile_code: str, db: Session = Depends(get_db)):
    plan = ProfileService.generate_build_plan(db, profile_code)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_code}' not found")
    return {"success": True, "data": plan}


@router.get("/cycles", response_model=schemas.PaginatedResponse[schemas.EbuildCycleTemplateResponse])
def list_cycles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    total, items = CycleService.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return {"total": total, "page": skip // limit + 1 if limit > 0 else 1, "page_size": limit, "items": items}


@router.get("/cycles/{cycle_code}", response_model=schemas.ApiResponse[schemas.EbuildCycleTemplateResponse])
def get_cycle(cycle_code: str, db: Session = Depends(get_db)):
    cycle = CycleService.get_by_code(db, cycle_code)
    if not cycle:
        raise HTTPException(status_code=404, detail=f"Cycle '{cycle_code}' not found")
    return {"success": True, "data": cycle}


@router.post("/cycles", response_model=schemas.ApiResponse[schemas.EbuildCycleTemplateResponse], status_code=201)
def create_cycle(data: schemas.EbuildCycleTemplateCreate, db: Session = Depends(get_db)):
    existing = CycleService.get_by_code(db, data.cycle_code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Cycle '{data.cycle_code}' already exists")
    cycle = CycleService.create(db, data.model_dump())
    return {"success": True, "data": cycle}


@router.patch("/cycles/{cycle_code}", response_model=schemas.ApiResponse[schemas.EbuildCycleTemplateResponse])
def update_cycle(cycle_code: str, data: schemas.EbuildCycleTemplateUpdate, db: Session = Depends(get_db)):
    cycle = CycleService.get_by_code(db, cycle_code)
    if not cycle:
        raise HTTPException(status_code=404, detail=f"Cycle '{cycle_code}' not found")
    cycle = CycleService.update(db, cycle, data.model_dump(exclude_unset=True))
    return {"success": True, "data": cycle}


@router.delete("/cycles/{cycle_code}", response_model=schemas.ApiResponse)
def delete_cycle(cycle_code: str, db: Session = Depends(get_db)):
    cycle = CycleService.get_by_code(db, cycle_code)
    if not cycle:
        raise HTTPException(status_code=404, detail=f"Cycle '{cycle_code}' not found")
    CycleService.delete(db, cycle)
    return {"success": True, "message": f"Cycle '{cycle_code}' deleted"}


@router.get("/modules", response_model=schemas.PaginatedResponse[schemas.EbuildModuleRegistryResponse])
def list_modules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    total, items = ModuleService.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return {"total": total, "page": skip // limit + 1 if limit > 0 else 1, "page_size": limit, "items": items}


@router.get("/modules/{module_code}", response_model=schemas.ApiResponse[schemas.EbuildModuleRegistryResponse])
def get_module(module_code: str, db: Session = Depends(get_db)):
    module = ModuleService.get_by_code(db, module_code)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_code}' not found")
    return {"success": True, "data": module}


@router.get("/modules/{module_code}/dependencies", response_model=schemas.ApiResponse[schemas.DependencyTreeResponse])
def get_module_dependencies(module_code: str, db: Session = Depends(get_db)):
    result = ModuleService.resolve_dependencies(db, module_code)
    if not result:
        raise HTTPException(status_code=404, detail=f"Module '{module_code}' not found")
    return {"success": True, "data": result}


@router.post("/modules", response_model=schemas.ApiResponse[schemas.EbuildModuleRegistryResponse], status_code=201)
def create_module(data: schemas.EbuildModuleRegistryCreate, db: Session = Depends(get_db)):
    existing = ModuleService.get_by_code(db, data.module_code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Module '{data.module_code}' already exists")
    module = ModuleService.create(db, data.model_dump())
    return {"success": True, "data": module}


@router.patch("/modules/{module_code}", response_model=schemas.ApiResponse[schemas.EbuildModuleRegistryResponse])
def update_module(module_code: str, data: schemas.EbuildModuleRegistryUpdate, db: Session = Depends(get_db)):
    module = ModuleService.get_by_code(db, module_code)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_code}' not found")
    module = ModuleService.update(db, module, data.model_dump(exclude_unset=True))
    return {"success": True, "data": module}


@router.delete("/modules/{module_code}", response_model=schemas.ApiResponse)
def delete_module(module_code: str, db: Session = Depends(get_db)):
    module = ModuleService.get_by_code(db, module_code)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_code}' not found")
    ModuleService.delete(db, module)
    return {"success": True, "message": f"Module '{module_code}' deleted"}


@router.get("/builds", response_model=schemas.PaginatedResponse[schemas.EbuildBuildQueueResponse])
def list_builds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    total, items = BuildService.get_all(db, skip=skip, limit=limit, status=status)
    return {"total": total, "page": skip // limit + 1 if limit > 0 else 1, "page_size": limit, "items": items}


@router.get("/builds/{build_id}", response_model=schemas.ApiResponse[schemas.EbuildBuildQueueResponse])
def get_build(build_id: str, db: Session = Depends(get_db)):
    entry = BuildService.get_by_build_id(db, build_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Build '{build_id}' not found")
    return {"success": True, "data": entry}


@router.post("/builds", response_model=schemas.ApiResponse[schemas.EbuildBuildQueueResponse], status_code=201)
def create_build(data: schemas.EbuildBuildQueueCreate, db: Session = Depends(get_db)):
    existing = BuildService.get_by_build_id(db, data.build_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Build '{data.build_id}' already exists")
    entry = BuildService.create(db, data.model_dump())
    return {"success": True, "data": entry}


@router.patch("/builds/{build_id}/status", response_model=schemas.ApiResponse[schemas.EbuildBuildQueueResponse])
def update_build_status(
    build_id: str,
    status: str,
    error_log: Optional[str] = None,
    db: Session = Depends(get_db),
):
    entry = BuildService.get_by_build_id(db, build_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Build '{build_id}' not found")
    entry = BuildService.update_status(db, entry, status, error_log=error_log)
    return {"success": True, "data": entry}


@router.delete("/builds/{build_id}", response_model=schemas.ApiResponse)
def delete_build(build_id: str, db: Session = Depends(get_db)):
    entry = BuildService.get_by_build_id(db, build_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Build '{build_id}' not found")
    BuildService.delete(db, entry)
    return {"success": True, "message": f"Build '{build_id}' deleted"}


@router.get("/companies", response_model=schemas.PaginatedResponse[schemas.EbuildCompanyInstanceResponse])
def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    total, items = CompanyService.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return {"total": total, "page": skip // limit + 1 if limit > 0 else 1, "page_size": limit, "items": items}


@router.get("/companies/{company_id}", response_model=schemas.ApiResponse[schemas.EbuildCompanyInstanceResponse])
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    instance = CompanyService.get_by_company_id(db, company_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
    return {"success": True, "data": instance}


@router.post("/companies", response_model=schemas.ApiResponse[schemas.EbuildCompanyInstanceResponse], status_code=201)
def create_company(data: schemas.EbuildCompanyInstanceCreate, db: Session = Depends(get_db)):
    existing = CompanyService.get_by_company_id(db, data.company_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Company '{data.company_id}' already registered")
    instance = CompanyService.create(db, data.model_dump())
    return {"success": True, "data": instance}


@router.patch("/companies/{company_id}", response_model=schemas.ApiResponse[schemas.EbuildCompanyInstanceResponse])
def update_company(company_id: uuid.UUID, data: schemas.EbuildCompanyInstanceUpdate, db: Session = Depends(get_db)):
    instance = CompanyService.get_by_company_id(db, company_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
    instance = CompanyService.update(db, instance, data.model_dump(exclude_unset=True))
    return {"success": True, "data": instance}


@router.delete("/companies/{company_id}", response_model=schemas.ApiResponse)
def delete_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    instance = CompanyService.get_by_company_id(db, company_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
    CompanyService.delete(db, instance)
    return {"success": True, "message": f"Company '{company_id}' unregistered"}


@router.post("/companies/{company_id}/health-check", response_model=schemas.ApiResponse[schemas.HealthCheckResponse])
def run_company_health_check(company_id: uuid.UUID, db: Session = Depends(get_db)):
    instance = CompanyService.get_by_company_id(db, company_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
    result = CompanyService.run_health_check(db, instance)
    return {"success": True, "data": result}
