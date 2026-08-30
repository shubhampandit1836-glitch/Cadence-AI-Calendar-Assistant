-- Identity integrity pass.
--
-- Two identity keys exist in this schema by design:
--   * oauth_user_id (TEXT, the Descope subject) — used by tables written directly from
--     agent/tool code (threads, user_memory, user_documents, document_chunks).
--   * users.id (UUID, internal primary key) — used by tables modeling a relationship
--     to the users row itself (connections, calendar_preferences).
-- The bug wasn't the two keys existing — it's that none of them had FK constraints, so
-- rows for a deleted user were silently orphaned. This adds the missing FKs without
-- renaming any column the application code depends on.

-- 1. calendar_preferences.user_id was TEXT with no FK, even though every caller
--    (require_session -> auth["user_id"]) passes the internal UUID. Drop orphans, then
--    convert to a real UUID FK so a bad ID fails fast instead of silently never matching.
DELETE FROM calendar_preferences
WHERE user_id !~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
   OR user_id::uuid NOT IN (SELECT id FROM users);

ALTER TABLE calendar_preferences
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid;

ALTER TABLE calendar_preferences
    ADD CONSTRAINT fk_calendar_preferences_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 2. oauth_user_id-keyed tables: drop orphans, then add FKs back to
--    users(oauth_user_id) so deleting a user cascades instead of leaving orphaned rows.
DELETE FROM threads WHERE oauth_user_id NOT IN (SELECT oauth_user_id FROM users);
DELETE FROM user_memory WHERE oauth_user_id NOT IN (SELECT oauth_user_id FROM users);
DELETE FROM user_documents WHERE oauth_user_id NOT IN (SELECT oauth_user_id FROM users);
DELETE FROM document_chunks WHERE oauth_user_id NOT IN (SELECT oauth_user_id FROM users);

ALTER TABLE threads
    ADD CONSTRAINT fk_threads_user
    FOREIGN KEY (oauth_user_id) REFERENCES users(oauth_user_id) ON DELETE CASCADE;

ALTER TABLE user_memory
    ADD CONSTRAINT fk_user_memory_user
    FOREIGN KEY (oauth_user_id) REFERENCES users(oauth_user_id) ON DELETE CASCADE;

ALTER TABLE user_documents
    ADD CONSTRAINT fk_user_documents_user
    FOREIGN KEY (oauth_user_id) REFERENCES users(oauth_user_id) ON DELETE CASCADE;

ALTER TABLE document_chunks
    ADD CONSTRAINT fk_document_chunks_user
    FOREIGN KEY (oauth_user_id) REFERENCES users(oauth_user_id) ON DELETE CASCADE;