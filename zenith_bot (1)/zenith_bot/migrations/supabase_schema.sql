-- =============================================================
-- Zenith Bot — Supabase Schema (Data Permanen)
-- Jalankan di Supabase SQL Editor
-- =============================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    password_hash TEXT,
    google_id VARCHAR(255) UNIQUE,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('bronze', 'silver', 'diamond')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    midtrans_order_id VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ
);

-- Sessions (JWT)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jwt_token TEXT NOT NULL,
    telegram_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Hermes Skills
CREATE TABLE IF NOT EXISTS hermes_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    content_type VARCHAR(20) DEFAULT 'text' CHECK (content_type IN ('text', 'pdf')),
    content_text TEXT NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    max_concurrent INTEGER DEFAULT 2,
    source VARCHAR(20) DEFAULT 'admin' CHECK (source IN ('admin', 'user')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hermes Self-Improvements (SL Hit Learning)
CREATE TABLE IF NOT EXISTS hermes_improvements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    saham VARCHAR(10) NOT NULL,
    entry NUMERIC(12, 2),
    sl NUMERIC(12, 2),
    skill_active TEXT,
    original_reason TEXT,
    lesson_learned TEXT,
    week_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG User Skills (Diamond)
CREATE TABLE IF NOT EXISTS rag_user_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(20) DEFAULT 'text',
    content_text TEXT NOT NULL,
    file_size INTEGER,
    category VARCHAR(50),
    vector_index TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG Admin Skills
CREATE TABLE IF NOT EXISTS rag_admin_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    content_text TEXT NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analisa History
CREATE TABLE IF NOT EXISTS analisa_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    saham VARCHAR(10) NOT NULL,
    tier_target VARCHAR(20),
    fase VARCHAR(10),
    entry NUMERIC(12, 2),
    tp NUMERIC(12, 2),
    sl NUMERIC(12, 2),
    reason TEXT,
    skill_used TEXT,
    provider_used VARCHAR(50),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'tp_hit', 'sl_hit', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signals Log
CREATE TABLE IF NOT EXISTS signals_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    saham VARCHAR(10) NOT NULL,
    entry NUMERIC(12, 2),
    tp NUMERIC(12, 2),
    sl NUMERIC(12, 2),
    tanggal_sinyal DATE NOT NULL DEFAULT CURRENT_DATE,
    tier_target VARCHAR(20),
    status VARCHAR(20) DEFAULT 'open',
    closed_at TIMESTAMPTZ
);

-- Admin Manual Users (influencer/mitra)
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL,
    username VARCHAR(100),
    tier VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    added_by BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin Suggestions ke Hermes
CREATE TABLE IF NOT EXISTS admin_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id BIGINT NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    context TEXT,
    hermes_result TEXT,
    is_signal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily Quotes
CREATE TABLE IF NOT EXISTS daily_quotes (
    id SERIAL PRIMARY KEY,
    quote_text TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed quotes
INSERT INTO daily_quotes (quote_text, author) VALUES
('The stock market is a device for transferring money from the impatient to the patient.', 'Warren Buffett'),
('The market is never wrong. Opinions often are.', 'Jesse Livermore'),
('Know what you own, and know why you own it.', 'Peter Lynch'),
('The most important rule is to play great defense, not great offense.', 'Paul Tudor Jones'),
('It is not whether you are right or wrong, but how much you make when right.', 'George Soros'),
('Successful trading is about probabilities, not certainties.', 'Mark Douglas'),
('Kenali musuhmu dan dirimu — kemenangan tidak perlu diragukan.', 'Sun Tzu'),
('The investor chief problem and worst enemy is likely to be himself.', 'Benjamin Graham'),
('Win or lose, everybody gets what they want out of the market.', 'Ed Seykota'),
('Kita adalah apa yang kita lakukan berulang-ulang. Keunggulan adalah kebiasaan.', 'Aristoteles')
ON CONFLICT DO NOTHING;
