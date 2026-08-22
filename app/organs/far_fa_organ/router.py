from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.organs.far_fa_organ import schemas
from app.organs.far_fa_organ.service import (
    FACategoryService, FAAssetService, FADisposalService,
    FARevaluationService, FAHealthService,
)

router = APIRouter()


# Health is served by sub_app.py — router health disabled (requires PostgreSQL)


@router.post("/categories", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return FACategoryService(db).create(data)


@router.get("/categories", response_model=List[schemas.CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return FACategoryService(db).get_all()


@router.get("/categories/{cat_id}", response_model=schemas.CategoryResponse)
def get_category(cat_id: int, db: Session = Depends(get_db)):
    cat = FACategoryService(db).get_by_id(cat_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.put("/categories/{cat_id}", response_model=schemas.CategoryResponse)
def update_category(cat_id: int, data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    cat = FACategoryService(db).update(cat_id, data)
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.post("/assets", response_model=schemas.AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(data: schemas.AssetCreate, db: Session = Depends(get_db)):
    return FAAssetService(db).create(data)


@router.post("/assets/{asset_id}/activate", response_model=schemas.AssetResponse)
def activate_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = FAAssetService(db).activate(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.get("/assets", response_model=List[schemas.AssetResponse])
def list_assets(db: Session = Depends(get_db)):
    return FAAssetService(db).get_all()


@router.get("/assets/{asset_id}", response_model=schemas.AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = FAAssetService(db).get_by_id(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.put("/assets/{asset_id}", response_model=schemas.AssetResponse)
def update_asset(asset_id: int, data: schemas.AssetUpdate, db: Session = Depends(get_db)):
    asset = FAAssetService(db).update(asset_id, data)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.post("/assets/{asset_id}/depreciation", response_model=List[schemas.DepreciationEntryResponse])
def run_depreciation(asset_id: int, data: schemas.DepreciationRun, db: Session = Depends(get_db)):
    entries = FAAssetService(db).run_depreciation(asset_id, data.period_id, data.run_date)
    if entries is None:
        raise HTTPException(400, "Cannot run depreciation on this asset")
    return entries


@router.post("/depreciation/run-all", response_model=List[schemas.DepreciationEntryResponse])
def run_all_depreciation(data: schemas.DepreciationRun, db: Session = Depends(get_db)):
    return FAAssetService(db).run_all_depreciation(data.period_id, data.run_date)


@router.get("/assets/{asset_id}/depreciation", response_model=List[schemas.DepreciationEntryResponse])
def get_depreciation_entries(asset_id: int, db: Session = Depends(get_db)):
    return FAAssetService(db).get_depreciation_entries(asset_id)


@router.post("/assets/{asset_id}/dispose", response_model=schemas.DisposalResponse)
def dispose_asset(asset_id: int, data: schemas.DisposalCreate, db: Session = Depends(get_db)):
    disposal = FAAssetService(db).dispose(asset_id, data)
    if not disposal:
        raise HTTPException(400, "Cannot dispose this asset")
    return disposal


@router.get("/assets/{asset_id}/disposals", response_model=List[schemas.DisposalResponse])
def get_disposals(asset_id: int, db: Session = Depends(get_db)):
    return FADisposalService(db).get_by_asset(asset_id)


@router.post("/assets/{asset_id}/revalue", response_model=schemas.RevaluationResponse)
def revalue_asset(asset_id: int, data: schemas.RevaluationCreate, db: Session = Depends(get_db)):
    reval = FAAssetService(db).revalue(asset_id, data)
    if not reval:
        raise HTTPException(400, "Cannot revalue this asset")
    return reval


@router.get("/assets/{asset_id}/revaluations", response_model=List[schemas.RevaluationResponse])
def get_revaluations(asset_id: int, db: Session = Depends(get_db)):
    return FARevaluationService(db).get_by_asset(asset_id)
