CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    oauth_user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_threads_oauth_user_id ON threads(oauth_user_id);