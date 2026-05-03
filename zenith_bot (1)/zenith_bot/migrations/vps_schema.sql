-- =============================================================
-- Zenith Bot — VPS PostgreSQL Schema (Cache Rolling)
-- Jalankan: psql -U zenith_user -d zenith_cache -f migrations/vps_schema.sql
-- =============================================================

-- Analisa cache (TTL 2 hari)
CREATE TABLE IF NOT EXISTS analisa_cache (
    id SERIAL PRIMARY KEY,
    saham VARCHAR(10) NOT NULL,
    kategori VARCHAR(50),
    indikator TEXT,
    fase VARCHAR(10) NOT NULL,
    entry NUMERIC(12, 2),
    tp NUMERIC(12, 2),
    sl NUMERIC(12, 2),
    reason TEXT,
    chart_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expired_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '2 days')
);

CREATE INDEX IF NOT EXISTS idx_analisa_saham ON analisa_cache(saham);
CREATE INDEX IF NOT EXISTS idx_analisa_expired ON analisa_cache(expired_at);

-- Price alerts
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    saham VARCHAR(10) NOT NULL,
    target_price NUMERIC(12, 2) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('above', 'below')),
    is_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(is_triggered);

-- Usage limits per user per day
CREATE TABLE IF NOT EXISTS usage_limits (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    request_count INTEGER DEFAULT 0,
    alert_count INTEGER DEFAULT 0,
    UNIQUE(user_id, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage_limits(user_id, usage_date);

-- Cleanup expired cache (jalankan via cron)
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM analisa_cache WHERE expired_at < NOW();
END;
$$ LANGUAGE plpgsql;
