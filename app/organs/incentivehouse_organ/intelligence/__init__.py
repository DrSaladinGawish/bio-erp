"""
IHE-ERP v2.3 Intelligence Layer
================================

Embedded intelligence layer for the IncentiveHouse ERP organ.  Provides
read-only self-healing analysis on top of the business modules:

  * audit       - AuditTrail model + audit_event() function
  * health      - System health checks (DB, tables, data quality)
  * gap         - ERP Builder Protocol gap analysis
  * backup      - Pre-change backup manager
  * neural      - 5 neural predictors (cashflow, anomaly, client, revenue, vendor)
  * or          - 6 most-used OR engines (LP, EOQ, PERT, Profit, BreakEven, Forecast)
  * scm         - 3 SCM analyzers (ValueChain, StrategicCost, Sustainability)

This layer NEVER writes to business tables.  All intelligence artifacts
live in dedicated *_staging tables and are surfaced via /api/v1/intelligence/*.

Public API surface:
    from app.organs.incentivehouse_organ.intelligence.audit import audit_event, AuditTrail
    from app.organs.incentivehouse_organ.intelligence.health import get_health_report
    from app.organs.incentivehouse_organ.intelligence.gap import run_gap_analysis
    from app.organs.incentivehouse_organ.intelligence.backup import backup_before_change
    from app.organs.incentivehouse_organ.intelligence.neural import run_all_predictors
    from app.organs.incentivehouse_organ.intelligence.or_module import run_or_solver
    from app.organs.incentivehouse_organ.intelligence.scm import run_scm_analysis
"""
__version__ = "2.3.0"
