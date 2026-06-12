-- Neural Prediction System — 4 new tables
-- Run: psql -U postgres -d bio_erp -f migrations/neural_system.sql

CREATE TABLE IF NOT EXISTS neural_predictions (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    prediction_type VARCHAR(50) NOT NULL,
    prediction_key  VARCHAR(255) NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    actual_value    DOUBLE PRECISION,
    features_snapshot JSONB,
    model_version   VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    prediction_date TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata_json   JSONB,
    UNIQUE(prediction_type, prediction_key, model_version)
);

CREATE TABLE IF NOT EXISTS neural_feature_store (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    feature_group   VARCHAR(50) NOT NULL,
    feature_key     VARCHAR(255) NOT NULL,
    feature_data    JSONB NOT NULL,
    feature_version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    valid_from      TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to        TIMESTAMP,
    UNIQUE(feature_group, feature_key, feature_version)
);

CREATE TABLE IF NOT EXISTS neural_training_history (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    model_name      VARCHAR(100) NOT NULL,
    model_version   VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    training_type   VARCHAR(50) NOT NULL DEFAULT 'full',
    training_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    dataset_size    INTEGER NOT NULL DEFAULT 0,
    accuracy        DOUBLE PRECISION,
    loss            DOUBLE PRECISION,
    duration_seconds DOUBLE PRECISION,
    parameters      JSONB,
    metrics         JSONB,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS neural_memory (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    memory_type     VARCHAR(50) NOT NULL,
    memory_key      VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,
    embedding       JSONB,
    importance      DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    access_count    INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMP,
    metadata_json   JSONB,
    user_id         INTEGER REFERENCES users(id),
    expires_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_neural_predictions_type ON neural_predictions(prediction_type);
CREATE INDEX IF NOT EXISTS ix_neural_predictions_key ON neural_predictions(prediction_key);
CREATE INDEX IF NOT EXISTS ix_neural_feature_store_group ON neural_feature_store(feature_group);
CREATE INDEX IF NOT EXISTS ix_neural_feature_store_key ON neural_feature_store(feature_key);
CREATE INDEX IF NOT EXISTS ix_neural_training_history_model ON neural_training_history(model_name);
CREATE INDEX IF NOT EXISTS ix_neural_memory_type ON neural_memory(memory_type);
CREATE INDEX IF NOT EXISTS ix_neural_memory_key ON neural_memory(memory_key);
CREATE INDEX IF NOT EXISTS ix_neural_memory_user ON neural_memory(user_id);
