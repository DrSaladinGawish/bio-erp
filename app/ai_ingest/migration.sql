-- AI Ingestion Module - Migration SQL
-- Run against bio_erp PostgreSQL database

-- Neural Nodes (knowledge graph entities)
CREATE TABLE IF NOT EXISTS neural_nodes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    label VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL DEFAULT 'entity',
    description TEXT,
    confidence FLOAT DEFAULT 0.0,
    metadata_json JSONB,
    source_document_id INTEGER REFERENCES ai_document_ingestion(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_neural_nodes_label ON neural_nodes(label);

-- Neural Links (relationships between neural nodes)
CREATE TABLE IF NOT EXISTS neural_links (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    source_node_id INTEGER NOT NULL REFERENCES neural_nodes(id) ON DELETE CASCADE,
    target_node_id INTEGER NOT NULL REFERENCES neural_nodes(id) ON DELETE CASCADE,
    link_type VARCHAR(50) NOT NULL DEFAULT 'relates_to',
    weight FLOAT DEFAULT 1.0,
    metadata_json JSONB
);
CREATE INDEX IF NOT EXISTS idx_neural_links_source ON neural_links(source_node_id);
CREATE INDEX IF NOT EXISTS idx_neural_links_target ON neural_links(target_node_id);

-- Document Ingestion Tracking
CREATE TABLE IF NOT EXISTS ai_document_ingestion (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    error_message TEXT,
    analysis_id INTEGER REFERENCES ai_document_analysis(id) ON DELETE SET NULL,
    archive_path VARCHAR(1000),
    is_archived BOOLEAN DEFAULT FALSE
);

-- Document Analysis Results
CREATE TABLE IF NOT EXISTS ai_document_analysis (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    document_id INTEGER NOT NULL REFERENCES ai_document_ingestion(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    raw_text TEXT,
    extracted_entities JSONB,
    extracted_patterns JSONB,
    neural_nodes JSONB,
    neural_links JSONB,
    summary TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    error_message TEXT,
    processing_time_ms INTEGER
);

-- AI Suggested Transactions (journal entries)
CREATE TABLE IF NOT EXISTS ai_suggested_transaction (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    document_id INTEGER NOT NULL REFERENCES ai_document_ingestion(id) ON DELETE CASCADE,
    analysis_id INTEGER REFERENCES ai_document_analysis(id) ON DELETE SET NULL,
    transaction_type VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    journal_lines JSONB NOT NULL,
    total_debit FLOAT DEFAULT 0.0,
    total_credit FLOAT DEFAULT 0.0,
    currency_id INTEGER REFERENCES currencies(id) ON DELETE SET NULL,
    branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'draft',
    review_notes TEXT,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    posted_jv_id INTEGER REFERENCES jv_headers(id) ON DELETE SET NULL,
    error_message TEXT
);

-- Neural Pattern Log
CREATE TABLE IF NOT EXISTS ai_neural_pattern_log (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    document_id INTEGER REFERENCES ai_document_ingestion(id) ON DELETE SET NULL,
    analysis_id INTEGER REFERENCES ai_document_analysis(id) ON DELETE SET NULL,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_key VARCHAR(500) NOT NULL,
    pattern_value TEXT,
    matched_entities JSONB,
    confidence FLOAT DEFAULT 0.0,
    source VARCHAR(50) DEFAULT 'local'
);
CREATE INDEX IF NOT EXISTS idx_neural_pattern_key ON ai_neural_pattern_log(pattern_key);

-- Surgery Audit Log
CREATE TABLE IF NOT EXISTS surgery_audit_log (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    surgery_id VARCHAR(36) NOT NULL,
    protocol VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    table_name VARCHAR(100),
    record_id INTEGER,
    snapshot_before JSONB,
    snapshot_after JSONB,
    error_message TEXT,
    performed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    metadata_json JSONB
);
CREATE INDEX IF NOT EXISTS idx_surgery_audit_surgery_id ON surgery_audit_log(surgery_id);
