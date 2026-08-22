from __future__ import annotations

import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.database import Base


class EbuildActivityProfile(Base):
    __tablename__ = "ebuild_activity_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_code = Column(String(20), unique=True, nullable=False, index=True)
    profile_name = Column(String(100), nullable=False)
    profile_name_ar = Column(String(100))
    description = Column(Text)
    sector_codes = Column(ARRAY(String), default=list)
    typical_legal_forms = Column(ARRAY(String), default=list)
    typical_size_range = Column(String(50))
    capital_structure_type = Column(String(50))
    required_modules = Column(ARRAY(String), nullable=False, default=list)
    optional_modules = Column(ARRAY(String), nullable=False, default=list)
    operational_cycles = Column(ARRAY(String), nullable=False, default=list)
    compliance_frameworks = Column(JSONB, default=dict)
    default_coa_template_id = Column(UUID(as_uuid=True))
    ebuild_package = Column(String(100), nullable=False)
    ebuild_version = Column(String(20), default="1.0.0")
    use_flags = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<EbuildActivityProfile(code='{self.profile_code}', name='{self.profile_name}')>"


class EbuildCycleTemplate(Base):
    __tablename__ = "ebuild_cycle_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_code = Column(String(50), unique=True, nullable=False, index=True)
    cycle_name = Column(String(100), nullable=False)
    cycle_name_ar = Column(String(100))
    description = Column(Text)
    applicable_profiles = Column(ARRAY(String), nullable=False, default=list)
    stages = Column(JSONB, nullable=False, default=list)
    document_templates = Column(JSONB, default=dict)
    financial_impact = Column(JSONB, default=dict)
    approval_workflow = Column(JSONB, default=dict)
    module_integrations = Column(ARRAY(String), default=list)
    ebuild_package = Column(String(100), nullable=False)
    use_flags = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EbuildCycleTemplate(code='{self.cycle_code}', name='{self.cycle_name}')>"


class EbuildModuleRegistry(Base):
    __tablename__ = "ebuild_module_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_code = Column(String(50), unique=True, nullable=False, index=True)
    module_name = Column(String(100), nullable=False)
    module_name_ar = Column(String(100))
    description = Column(Text)
    current_version = Column(String(20), default="1.0.0")
    min_bio_erp_version = Column(String(20), default="1.0.0")
    hard_dependencies = Column(ARRAY(String), default=list)
    soft_dependencies = Column(ARRAY(String), default=list)
    conflicts = Column(ARRAY(String), default=list)
    available_use_flags = Column(ARRAY(String), default=list)
    default_use_flags = Column(ARRAY(String), default=list)
    tables_created = Column(ARRAY(String), default=list)
    api_prefix = Column(String(100))
    neural_links = Column(JSONB, default=dict)
    applicable_profiles = Column(ARRAY(String), default=list)
    is_core = Column(Boolean, default=False)
    ebuild_category = Column(String(50), nullable=False)
    ebuild_package = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EbuildModuleRegistry(code='{self.module_code}', name='{self.module_name}')>"


class EbuildBuildQueue(Base):
    __tablename__ = "ebuild_build_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    build_id = Column(String(50), unique=True, nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True))
    company_name = Column(String(200))
    activity_profile_code = Column(String(20), ForeignKey("ebuild_activity_profiles.profile_code"))
    selected_modules = Column(ARRAY(String), nullable=False, default=list)
    selected_use_flags = Column(ARRAY(String), nullable=False, default=list)
    build_config = Column(JSONB, default=dict)
    status = Column(String(20), default="pending")
    phases = Column(JSONB, default=list)
    build_log = Column(Text)
    error_log = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EbuildBuildQueue(id='{self.build_id}', status='{self.status}')>"


class EbuildCompanyInstance(Base):
    __tablename__ = "ebuild_company_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    company_name_ar = Column(String(200))
    activity_profile_code = Column(String(20), ForeignKey("ebuild_activity_profiles.profile_code"))
    deployed_modules = Column(JSONB, default=dict)
    active_cycles = Column(ARRAY(String), default=list)
    company_config = Column(JSONB, default=dict)
    health_score = Column(Numeric(3, 2), default=0.00)
    last_health_check = Column(DateTime(timezone=True))
    deployment_status = Column(String(20), default="active")
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<EbuildCompanyInstance(name='{self.company_name}', profile='{self.activity_profile_code}')>"
