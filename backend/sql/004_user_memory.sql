CREATE TABLE IF NOT EXISTS user_memory (
    id SERIAL PRIMARY KEY,
    oauth_user_id TEXT NOT NULL,
    fact TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_user ON user_memory(oauth_user_id);