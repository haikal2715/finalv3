-- =============================================================
-- Zenith Bot — Supabase Additional Schema
-- Jalankan setelah supabase_schema.sql
-- =============================================================

-- Tracking skill aktif per user (Silver/Diamond)
CREATE TABLE IF NOT EXISTS user_active_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES hermes_skills(id) ON DELETE CASCADE,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_user_active_skills_user ON user_active_skills(user_id);

-- Tambah kolom reset password ke users
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS reset_token TEXT,
    ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ;
