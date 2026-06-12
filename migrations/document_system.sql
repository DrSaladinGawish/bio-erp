-- Document Management System — PostgreSQL Migration
-- Run: psql -d bio_erp -f migrations/document_system.sql

CREATE TABLE IF NOT EXISTS supporting_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name VARCHAR(32) NOT NULL,
    function_name VARCHAR(32) NOT NULL,
    transaction_table VARCHAR(64) NOT NULL,
    transaction_id VARCHAR(64) NOT NULL,
    original_usb_path TEXT,
    archive_path TEXT NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_ext VARCHAR(10) NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    status VARCHAR(16) DEFAULT 'linked' CHECK (status IN ('linked','verified','missing','modified')),
    uploaded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_module ON supporting_documents(module_name, function_name);
CREATE INDEX IF NOT EXISTS idx_docs_transaction ON supporting_documents(transaction_table, transaction_id);
CREATE INDEX IF NOT EXISTS idx_docs_status ON supporting_documents(status);
CREATE INDEX IF NOT EXISTS idx_docs_hash ON supporting_documents(file_hash_sha256);

CREATE TABLE IF NOT EXISTS document_modules (
    module_name VARCHAR(32) NOT NULL,
    function_name VARCHAR(32) NOT NULL,
    transaction_table VARCHAR(64) NOT NULL,
    description TEXT,
    filename_pattern VARCHAR(255),
    PRIMARY KEY (module_name, function_name)
);
