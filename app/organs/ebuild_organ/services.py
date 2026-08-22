from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from collections import deque

from sqlalchemy.orm import Session

from app.organs.ebuild_organ.models import (
    EbuildActivityProfile,
    EbuildCycleTemplate,
    EbuildModuleRegistry,
    EbuildBuildQueue,
    EbuildCompanyInstance,
)

logger = logging.getLogger(__name__)


def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
    try:
        from app.brain.eventbridge import EventBridge
        EventBridge.emit(event_type, payload)
    except ImportError:
        logger.info("[Event] %s: %s", event_type, payload)


class ProfileService:

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True):
        q = db.query(EbuildActivityProfile)
        if active_only:
            q = q.filter(EbuildActivityProfile.is_active.is_(True))
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[EbuildActivityProfile]:
        return db.query(EbuildActivityProfile).filter(
            EbuildActivityProfile.profile_code == code
        ).first()

    @staticmethod
    def get_by_id(db: Session, profile_id: uuid.UUID) -> Optional[EbuildActivityProfile]:
        return db.query(EbuildActivityProfile).filter(
            EbuildActivityProfile.id == profile_id
        ).first()

    @staticmethod
    def create(db: Session, data: dict) -> EbuildActivityProfile:
        profile = EbuildActivityProfile(**data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        emit_event("profile_created", {"profile_code": profile.profile_code})
        return profile

    @staticmethod
    def update(db: Session, profile: EbuildActivityProfile, data: dict) -> EbuildActivityProfile:
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete(db: Session, profile: EbuildActivityProfile) -> None:
        db.delete(profile)
        db.commit()

    @staticmethod
    def generate_build_plan(db: Session, profile_code: str) -> Optional[Dict[str, Any]]:
        profile = ProfileService.get_by_code(db, profile_code)
        if not profile:
            return None

        all_codes = list(set(profile.required_modules + profile.optional_modules))
        modules = db.query(EbuildModuleRegistry).filter(
            EbuildModuleRegistry.module_code.in_(all_codes)
        ).all()
        module_map = {m.module_code: m for m in modules}

        required = [module_map[c] for c in profile.required_modules if c in module_map]
        optional = [module_map[c] for c in profile.optional_modules if c in module_map]

        resolved = set(profile.required_modules)
        for mod in required:
            for dep in (mod.hard_dependencies or []):
                if dep not in resolved:
                    resolved.add(dep)

        cycles = db.query(EbuildCycleTemplate).filter(
            EbuildCycleTemplate.cycle_code.in_(profile.operational_cycles),
            EbuildCycleTemplate.is_active.is_(True),
        ).all()

        return {
            "profile": profile,
            "required_modules": required,
            "optional_modules": optional,
            "resolved_dependencies": sorted(resolved),
            "cycles": cycles,
            "recommended_use_flags": profile.use_flags or [],
            "compliance_frameworks": profile.compliance_frameworks or {},
        }


class CycleService:

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True):
        q = db.query(EbuildCycleTemplate)
        if active_only:
            q = q.filter(EbuildCycleTemplate.is_active.is_(True))
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[EbuildCycleTemplate]:
        return db.query(EbuildCycleTemplate).filter(
            EbuildCycleTemplate.cycle_code == code
        ).first()

    @staticmethod
    def create(db: Session, data: dict) -> EbuildCycleTemplate:
        cycle = EbuildCycleTemplate(**data)
        db.add(cycle)
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def update(db: Session, cycle: EbuildCycleTemplate, data: dict) -> EbuildCycleTemplate:
        for key, value in data.items():
            if value is not None:
                setattr(cycle, key, value)
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def delete(db: Session, cycle: EbuildCycleTemplate) -> None:
        db.delete(cycle)
        db.commit()


class ModuleService:

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True):
        q = db.query(EbuildModuleRegistry)
        if active_only:
            q = q.filter(EbuildModuleRegistry.is_active.is_(True))
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[EbuildModuleRegistry]:
        return db.query(EbuildModuleRegistry).filter(
            EbuildModuleRegistry.module_code == code
        ).first()

    @staticmethod
    def create(db: Session, data: dict) -> EbuildModuleRegistry:
        module = EbuildModuleRegistry(**data)
        db.add(module)
        db.commit()
        db.refresh(module)
        return module

    @staticmethod
    def update(db: Session, module: EbuildModuleRegistry, data: dict) -> EbuildModuleRegistry:
        for key, value in data.items():
            if value is not None:
                setattr(module, key, value)
        db.commit()
        db.refresh(module)
        return module

    @staticmethod
    def delete(db: Session, module: EbuildModuleRegistry) -> None:
        db.delete(module)
        db.commit()

    @staticmethod
    def resolve_dependencies(db: Session, module_code: str) -> Optional[Dict[str, Any]]:
        module = ModuleService.get_by_code(db, module_code)
        if not module:
            return None

        all_m = {m.module_code: m for m in db.query(EbuildModuleRegistry).all()}
        visited = set()
        tree = []
        q = deque([(module_code, 0)])
        conflicts = []
        missing = []

        while q:
            code, depth = q.popleft()
            if code in visited:
                continue
            visited.add(code)

            entry = all_m.get(code)
            if not entry:
                missing.append(code)
                continue

            deps = list(entry.hard_dependencies or [])
            tree.append({
                "module_code": code,
                "module_name": entry.module_name,
                "depth": depth,
                "dependencies": deps,
                "is_core": entry.is_core,
            })

            for dep in deps:
                q.append((dep, depth + 1))

            for conflict in (entry.conflicts or []):
                if conflict in visited:
                    conflicts.append(conflict)

        return {
            "root_module": module_code,
            "tree": tree,
            "conflicts": conflicts,
            "missing_dependencies": missing,
        }


class BuildService:

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None):
        q = db.query(EbuildBuildQueue)
        if status:
            q = q.filter(EbuildBuildQueue.status == status)
        q = q.order_by(EbuildBuildQueue.created_at.desc())
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def get_by_build_id(db: Session, build_id: str) -> Optional[EbuildBuildQueue]:
        return db.query(EbuildBuildQueue).filter(
            EbuildBuildQueue.build_id == build_id
        ).first()

    @staticmethod
    def create(db: Session, data: dict) -> EbuildBuildQueue:
        if not data.get("build_id"):
            data["build_id"] = f"build-{uuid.uuid4().hex[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        entry = EbuildBuildQueue(**data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        emit_event("erp_build_started", {
            "build_id": entry.build_id,
            "company_name": entry.company_name,
            "profile_code": entry.activity_profile_code,
        })
        return entry

    @staticmethod
    def update_status(
        db: Session, entry: EbuildBuildQueue, status: str, error_log: Optional[str] = None
    ) -> EbuildBuildQueue:
        entry.status = status
        if status == "in_progress" and not entry.started_at:
            entry.started_at = datetime.now()
        if status in ("completed", "failed"):
            entry.completed_at = datetime.now()
            emit_event(
                "erp_build_completed" if status == "completed" else "erp_build_failed",
                {"build_id": entry.build_id, "company_name": entry.company_name, "status": status},
            )
        if error_log:
            entry.error_log = (entry.error_log or "") + "\n" + error_log
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def delete(db: Session, entry: EbuildBuildQueue) -> None:
        db.delete(entry)
        db.commit()


class CompanyService:

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True):
        q = db.query(EbuildCompanyInstance)
        if active_only:
            q = q.filter(EbuildCompanyInstance.is_active.is_(True))
        q = q.order_by(EbuildCompanyInstance.created_at.desc())
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def get_by_company_id(db: Session, company_id: uuid.UUID) -> Optional[EbuildCompanyInstance]:
        return db.query(EbuildCompanyInstance).filter(
            EbuildCompanyInstance.company_id == company_id
        ).first()

    @staticmethod
    def create(db: Session, data: dict) -> EbuildCompanyInstance:
        instance = EbuildCompanyInstance(**data)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        emit_event("company_instance_created", {
            "company_id": str(instance.company_id),
            "company_name": instance.company_name,
            "profile_code": instance.activity_profile_code,
        })
        return instance

    @staticmethod
    def update(db: Session, instance: EbuildCompanyInstance, data: dict) -> EbuildCompanyInstance:
        for key, value in data.items():
            if value is not None:
                setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        return instance

    @staticmethod
    def delete(db: Session, instance: EbuildCompanyInstance) -> None:
        db.delete(instance)
        db.commit()

    @staticmethod
    def run_health_check(db: Session, instance: EbuildCompanyInstance) -> Dict[str, Any]:
        score = 0.0
        recommendations = []

        if instance.deployed_modules:
            score += min(len(instance.deployed_modules) * 2.0, 5.0)
        else:
            recommendations.append("No modules deployed")

        if instance.active_cycles:
            score += 2.0
        else:
            recommendations.append("No operational cycles configured")

        if instance.company_config:
            score += 1.0
        else:
            recommendations.append("Company configuration is empty")

        if instance.deployment_status == "active":
            score += 1.0
        if instance.activity_profile_code:
            score += 1.0

        instance.health_score = min(score, 9.99)
        instance.last_health_check = datetime.now()
        db.commit()
        db.refresh(instance)

        return {
            "company_id": instance.company_id,
            "company_name": instance.company_name,
            "health_score": float(instance.health_score),
            "module_count": len(instance.deployed_modules or {}),
            "cycles_active": len(instance.active_cycles or []),
            "last_check": instance.last_health_check,
            "recommendations": recommendations,
        }
