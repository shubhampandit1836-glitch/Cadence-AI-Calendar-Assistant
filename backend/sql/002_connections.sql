CREATE TABLE IF NOT EXISTS connections (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('calendar', 'gmail', 'slack')),
  status TEXT NOT NULL CHECK (status IN ('connected', 'disconnected', 'pending')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, provider)
); 