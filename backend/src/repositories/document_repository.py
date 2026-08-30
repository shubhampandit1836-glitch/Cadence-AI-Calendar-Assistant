from typing import Any, Dict, List, cast
from src.config.db_pool import get_pool, reset_pool

async def insert_document(
    doc_id: str,
    oauth_user_id: str,
    filename: str,
    file_size: int,
    doc_type: str,
    summary: str
) -> None:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_documents (id, oauth_user_id, filename, file_size, doc_type, summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (doc_id, oauth_user_id, filename, file_size, doc_type, summary),
                )
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise

async def delete_documents_by_filename(oauth_user_id: str, filename: str) -> None:
    """Remove any existing document(s) with this exact filename for this user before a
    fresh upload is inserted. Chunks cascade-delete automatically via the FK."""
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM user_documents WHERE oauth_user_id = %s AND filename = %s",
                    (oauth_user_id, filename),
                )
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise

async def insert_document_chunks(
    doc_id: str,
    oauth_user_id: str,
    chunks: List[Dict[str, Any]]
) -> None:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                for chunk in chunks:
                    emb_str = f"[{','.join(str(x) for x in chunk['embedding'])}]"
                    await conn.execute(
                        """
                        INSERT INTO document_chunks (document_id, oauth_user_id, chunk_index, content, embedding)
                        VALUES (%s, %s, %s, %s, %s::vector)
                        """,
                        (doc_id, oauth_user_id, chunk["index"], chunk["content"], emb_str),
                    )
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise

async def list_user_documents(oauth_user_id: str) -> List[Dict[str, Any]]:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                cur = await conn.execute(
                    """
                    SELECT id, filename, file_size, doc_type, summary, created_at
                    FROM user_documents
                    WHERE oauth_user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (oauth_user_id,),
                )
                rows = cast(List[Dict[str, Any]], await cur.fetchall())
                return [
                    {
                        "id": r["id"],
                        "filename": r["filename"],
                        "file_size": r["file_size"],
                        "doc_type": r["doc_type"],
                        "summary": r["summary"],
                        "created_at": r["created_at"].isoformat(),
                    }
                    for r in rows
                ]
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise

async def delete_user_document(doc_id: str, oauth_user_id: str) -> bool:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "DELETE FROM user_documents WHERE id = %s AND oauth_user_id = %s",
                    (doc_id, oauth_user_id),
                )
                return cur.rowcount > 0
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise


async def delete_all_documents(oauth_user_id: str) -> int:
    """Delete every document (and its chunks, via cascade) for this user. Returns how many
    documents were removed, so the caller can report an accurate count back to the user."""
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "DELETE FROM user_documents WHERE oauth_user_id = %s",
                    (oauth_user_id,),
                )
                return cur.rowcount
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise


async def similarity_search_chunks(
    oauth_user_id: str,
    query_embedding: List[float],
    top_k: int = 4,
    filename: str | None = None,
) -> List[Dict[str, Any]]:
    emb_str = f"[{','.join(str(x) for x in query_embedding)}]"
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                if filename:
                    cur = await conn.execute(
                        """
                        SELECT c.content, d.filename, d.doc_type, (c.embedding <=> %s::vector) AS distance
                        FROM document_chunks c
                        JOIN user_documents d ON c.document_id = d.id
                        WHERE c.oauth_user_id = %s AND d.filename = %s
                        ORDER BY distance ASC
                        LIMIT %s
                        """,
                        (emb_str, oauth_user_id, filename, top_k),
                    )
                else:
                    cur = await conn.execute(
                        """
                        SELECT c.content, d.filename, d.doc_type, (c.embedding <=> %s::vector) AS distance
                        FROM document_chunks c
                        JOIN user_documents d ON c.document_id = d.id
                        WHERE c.oauth_user_id = %s
                        ORDER BY distance ASC
                        LIMIT %s
                        """,
                        (emb_str, oauth_user_id, top_k),
                    )
                rows = cast(List[Dict[str, Any]], await cur.fetchall())
                return [
                    {
                        "content": r["content"],
                        "filename": r["filename"],
                        "doc_type": r["doc_type"],
                        "score": round(1.0 - float(r["distance"]), 3),
                    }
                    for r in rows
                ]
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise