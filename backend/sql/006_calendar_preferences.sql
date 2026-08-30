CREATE TABLE IF NOT EXISTS calendar_preferences (
    user_id TEXT PRIMARY KEY,
    selected_calendar_ids TEXT[] NOT NULL DEFAULT ARRAY['primary'],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);