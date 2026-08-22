from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, TypeVar, Generic

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int = 1
    page_size: int = 20
    items: List[T]


class EbuildActivityProfileBase(BaseModel):
    profile_code: str = Field(..., max_length=20)
    profile_name: str = Field(..., max_length=100)
    profile_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    sector_codes: List[str] = []
    typical_legal_forms: List[str] = []
    typical_size_range: Optional[str] = Field(None, max_length=50)
    capital_structure_type: Optional[str] = Field(None, max_length=50)
    required_modules: List[str] = []
    optional_modules: List[str] = []
    operational_cycles: List[str] = []
    compliance_frameworks: Dict[str, Any] = {}
    default_coa_template_id: Optional[uuid.UUID] = None
    ebuild_package: str = Field(..., max_length=100)
    ebuild_version: str = "1.0.0"
    use_flags: List[str] = []
    is_active: bool = True


class EbuildActivityProfileCreate(EbuildActivityProfileBase):
    pass


class EbuildActivityProfileUpdate(BaseModel):
    profile_code: Optional[str] = Field(None, max_length=20)
    profile_name: Optional[str] = Field(None, max_length=100)
    profile_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    sector_codes: Optional[List[str]] = None
    typical_legal_forms: Optional[List[str]] = None
    typical_size_range: Optional[str] = Field(None, max_length=50)
    capital_structure_type: Optional[str] = Field(None, max_length=50)
    required_modules: Optional[List[str]] = None
    optional_modules: Optional[List[str]] = None
    operational_cycles: Optional[List[str]] = None
    compliance_frameworks: Optional[Dict[str, Any]] = None
    default_coa_template_id: Optional[uuid.UUID] = None
    ebuild_package: Optional[str] = Field(None, max_length=100)
    ebuild_version: Optional[str] = Field(None, max_length=20)
    use_flags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EbuildActivityProfileResponse(EbuildActivityProfileBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EbuildCycleTemplateBase(BaseModel):
    cycle_code: str = Field(..., max_length=50)
    cycle_name: str = Field(..., max_length=100)
    cycle_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    applicable_profiles: List[str] = []
    stages: List[Dict[str, Any]] = []
    document_templates: Dict[str, Any] = {}
    financial_impact: Dict[str, Any] = {}
    approval_workflow: Dict[str, Any] = {}
    module_integrations: List[str] = []
    ebuild_package: str = Field(..., max_length=100)
    use_flags: List[str] = []
    is_active: bool = True


class EbuildCycleTemplateCreate(EbuildCycleTemplateBase):
    pass


class EbuildCycleTemplateUpdate(BaseModel):
    cycle_code: Optional[str] = Field(None, max_length=50)
    cycle_name: Optional[str] = Field(None, max_length=100)
    cycle_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    applicable_profiles: Optional[List[str]] = None
    stages: Optional[List[Dict[str, Any]]] = None
    document_templates: Optional[Dict[str, Any]] = None
    financial_impact: Optional[Dict[str, Any]] = None
    approval_workflow: Optional[Dict[str, Any]] = None
    module_integrations: Optional[List[str]] = None
    ebuild_package: Optional[str] = Field(None, max_length=100)
    use_flags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EbuildCycleTemplateResponse(EbuildCycleTemplateBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EbuildModuleRegistryBase(BaseModel):
    module_code: str = Field(..., max_length=50)
    module_name: str = Field(..., max_length=100)
    module_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    current_version: str = "1.0.0"
    min_bio_erp_version: str = "1.0.0"
    hard_dependencies: List[str] = []
    soft_dependencies: List[str] = []
    conflicts: List[str] = []
    available_use_flags: List[str] = []
    default_use_flags: List[str] = []
    tables_created: List[str] = []
    api_prefix: Optional[str] = Field(None, max_length=100)
    neural_links: Dict[str, Any] = {}
    applicable_profiles: List[str] = []
    is_core: bool = False
    ebuild_category: str = Field(..., max_length=50)
    ebuild_package: str = Field(..., max_length=100)
    is_active: bool = True


class EbuildModuleRegistryCreate(EbuildModuleRegistryBase):
    pass


class EbuildModuleRegistryUpdate(BaseModel):
    module_code: Optional[str] = Field(None, max_length=50)
    module_name: Optional[str] = Field(None, max_length=100)
    module_name_ar: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    current_version: Optional[str] = Field(None, max_length=20)
    min_bio_erp_version: Optional[str] = Field(None, max_length=20)
    hard_dependencies: Optional[List[str]] = None
    soft_dependencies: Optional[List[str]] = None
    conflicts: Optional[List[str]] = None
    available_use_flags: Optional[List[str]] = None
    default_use_flags: Optional[List[str]] = None
    tables_created: Optional[List[str]] = None
    api_prefix: Optional[str] = Field(None, max_length=100)
    neural_links: Optional[Dict[str, Any]] = None
    applicable_profiles: Optional[List[str]] = None
    is_core: Optional[bool] = None
    ebuild_category: Optional[str] = Field(None, max_length=50)
    ebuild_package: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class EbuildModuleRegistryResponse(EbuildModuleRegistryBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EbuildBuildQueueBase(BaseModel):
    build_id: str = Field(..., max_length=50)
    company_id: Optional[uuid.UUID] = None
    company_name: Optional[str] = Field(None, max_length=200)
    activity_profile_code: Optional[str] = Field(None, max_length=20)
    selected_modules: List[str] = []
    selected_use_flags: List[str] = []
    build_config: Dict[str, Any] = {}
    status: str = "pending"
    phases: List[Dict[str, Any]] = []


class EbuildBuildQueueCreate(EbuildBuildQueueBase):
    pass


class EbuildBuildQueueUpdate(BaseModel):
    status: Optional[str] = None
    build_config: Optional[Dict[str, Any]] = None
    phases: Optional[List[Dict[str, Any]]] = None
    build_log: Optional[str] = None
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EbuildBuildQueueResponse(EbuildBuildQueueBase):
    id: uuid.UUID
    build_log: Optional[str] = None
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EbuildCompanyInstanceBase(BaseModel):
    company_id: uuid.UUID
    company_name: str = Field(..., max_length=200)
    company_name_ar: Optional[str] = Field(None, max_length=200)
    activity_profile_code: Optional[str] = Field(None, max_length=20)
    deployed_modules: Dict[str, Any] = {}
    active_cycles: List[str] = []
    company_config: Dict[str, Any] = {}
    deployment_status: str = "active"
    is_active: bool = True


class EbuildCompanyInstanceCreate(EbuildCompanyInstanceBase):
    pass


class EbuildCompanyInstanceUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=200)
    company_name_ar: Optional[str] = Field(None, max_length=200)
    activity_profile_code: Optional[str] = Field(None, max_length=20)
    deployed_modules: Optional[Dict[str, Any]] = None
    active_cycles: Optional[List[str]] = None
    company_config: Optional[Dict[str, Any]] = None
    deployment_status: Optional[str] = None
    is_active: Optional[bool] = None


class EbuildCompanyInstanceResponse(EbuildCompanyInstanceBase):
    id: uuid.UUID
    health_score: float = 0.0
    last_health_check: Optional[datetime] = None
    deployed_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class BuildPlanResponse(BaseModel):
    profile: EbuildActivityProfileResponse
    required_modules: List[EbuildModuleRegistryResponse]
    optional_modules: List[EbuildModuleRegistryResponse]
    resolved_dependencies: List[str]
    cycles: List[EbuildCycleTemplateResponse]
    recommended_use_flags: List[str]
    compliance_frameworks: Dict[str, List[str]]


class DependencyNode(BaseModel):
    module_code: str
    module_name: str
    depth: int
    dependencies: List[str]
    is_core: bool


class DependencyTreeResponse(BaseModel):
    root_module: str
    tree: List[DependencyNode]
    conflicts: List[str]
    missing_dependencies: List[str]


class HealthCheckResponse(BaseModel):
    company_id: uuid.UUID
    company_name: str
    health_score: float
    module_count: int
    cycles_active: int
    last_check: Optional[datetime] = None
    recommendations: List[str] = []
