-- ═══════════════════════════════════════════════════════════
-- P3-D2: SCM Staging Schema — Strict Separation from Production
-- Run this ONCE against your bio_erp database
-- ═════════════════════════════════════════════════════════==

CREATE SCHEMA IF NOT EXISTS scm_staging;

-- Cost Analysis Results (Advisory only — never auto-promoted)
CREATE TABLE IF NOT EXISTS scm_staging.cost_analysis (
    id              SERIAL PRIMARY KEY,
    event_id        INTEGER NOT NULL,
    analysis_type   VARCHAR(100) NOT NULL,
    input_data      JSONB DEFAULT '{}',
    results         JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    confidence_score DECIMAL(5,4) CHECK (confidence_score BETWEEN 0 AND 1),
    created_by      VARCHAR(100) DEFAULT 'scm_system',
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cost_analysis_event ON scm_staging.cost_analysis(event_id);
CREATE INDEX IF NOT EXISTS idx_cost_analysis_type  ON scm_staging.cost_analysis(analysis_type);

-- Vendor Scorecards (Promotable to suppliers.rating)
CREATE TABLE IF NOT EXISTS scm_staging.vendor_scorecards (
    id                SERIAL PRIMARY KEY,
    vendor_id         INTEGER NOT NULL,
    evaluation_period VARCHAR(50) NOT NULL,  -- e.g. '2026-Q2'
    quality_score     DECIMAL(5,2) CHECK (quality_score BETWEEN 0 AND 100),
    delivery_score    DECIMAL(5,2) CHECK (delivery_score BETWEEN 0 AND 100),
    price_score       DECIMAL(5,2) CHECK (price_score BETWEEN 0 AND 100),
    service_score     DECIMAL(5,2) CHECK (service_score BETWEEN 0 AND 100),
    overall_score     DECIMAL(5,2) CHECK (overall_score BETWEEN 0 AND 100),
    notes             TEXT,
    created_by        VARCHAR(100) DEFAULT 'scm_system',
    created_at        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scorecards_vendor ON scm_staging.vendor_scorecards(vendor_id);

-- Budget Forecasts (Promotable to events.projected_profit)
CREATE TABLE IF NOT EXISTS scm_staging.budget_forecasts (
    id                SERIAL PRIMARY KEY,
    event_id          INTEGER NOT NULL,
    forecast_period   VARCHAR(50) NOT NULL,
    projected_revenue DECIMAL(18,2),
    projected_cost    DECIMAL(18,2),
    projected_profit  DECIMAL(18,2),
    variance_notes    TEXT,
    created_by        VARCHAR(100) DEFAULT 'scm_system',
    created_at        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_forecasts_event ON scm_staging.budget_forecasts(event_id);

-- Promotion Requests (Audit trail for staging → production)
CREATE TABLE IF NOT EXISTS scm_staging.promotion_requests (
    id              SERIAL PRIMARY KEY,
    staging_id      INTEGER NOT NULL,
    staging_table   VARCHAR(100) NOT NULL,
    requested_by    VARCHAR(100) NOT NULL,
    request_reason  TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    requested_at    TIMESTAMP DEFAULT NOW(),
    approved_by     VARCHAR(100),
    approved_at     TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_promo_status ON scm_staging.promotion_requests(status);

-- Audit comment
COMMENT ON SCHEMA scm_staging IS 'SCM Module staging area — STRICT SEPARATION from production. Reads from public schema, writes here only. Promotion requires explicit admin approval.';
