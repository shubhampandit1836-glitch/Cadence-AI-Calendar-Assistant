CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS user_documents (
    id TEXT PRIMARY KEY,
    oauth_user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INT NOT NULL,
    doc_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_documents_user ON user_documents(oauth_user_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES user_documents(id) ON DELETE CASCADE,
    oauth_user_id TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doc_chunks_user ON document_chunks(oauth_user_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);