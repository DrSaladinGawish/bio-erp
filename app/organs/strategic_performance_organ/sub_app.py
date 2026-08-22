"""
Strategic Performance Measurement Sub-Application for BIO-ERP v5
================================================================
Mount at: app.mount("/api/v1/strategic-performance", strategic_performance_app)

15 techniques: BSC, EFQM, TQM, KPI Frameworks, Performance Dashboards,
Benchmarking, Strategy Maps, Performance Contracts, OKR Cascading,
Performance Reviews, Gap Analysis, Improvement Plans, BSC Variance,
Performance Measurement Systems, Results-Based Management
"""

from fastapi import FastAPI

from app.organs.strategic_performance_organ.router import router as perf_router

strategic_performance_app = FastAPI(
    title="Strategic Performance Measurement Microservice",
    description="15 strategic performance techniques — BSC, EFQM, TQM, KPI Frameworks, "
    "Dashboards, Benchmarking, Strategy Maps, Contracts, OKR, Reviews, "
    "Gap Analysis, Improvement Plans, BSC Variance, Measurement Systems, RBM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

strategic_performance_app.include_router(perf_router)
