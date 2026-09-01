from typing import Any, Dict, List
from datetime import datetime, timezone
import psycopg
from src.config.db_pool import get_pool, reset_pool


def _make_title(text: str, max_len: int = 28) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


async def upsert_thread(thread_id: str, oauth_user_id: str, last_message: str) -> None:
    """On first insert, derive a short title from the message via _make_title. On
    conflict (existing thread), only bump updated_at — the title stays as it was set
    on creation, so it doesn't keep changing every time the user sends a new message."""
    title = _make_title(last_message)
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO threads (id, oauth_user_id, title, updated_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET updated_at = now()
                    """,
                    (thread_id, oauth_user_id, title),
                )
            return
        except psycopg.errors.ForeignKeyViolation:
            # Permanent — the oauth_user_id doesn't exist in `users`. Retrying or
            # resetting the pool won't fix this and would break other concurrent
            # queries sharing the pool. Raise immediately.
            raise
        except psycopg.errors.IntegrityError:
            raise
        except Exception:
            # Only genuinely transient failures (dropped connection, etc.) should
            # reset the shared pool.
            if attempt == 1:
                await reset_pool()
                continue
            raise


async def touch_thread(thread_id: str) -> None:
    now = datetime.now(timezone.utc)
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute("UPDATE threads SET updated_at = %s WHERE id = %s", (now, thread_id))
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise


async def list_threads(oauth_user_id: str) -> List[Dict[str, Any]]:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT id, title, updated_at FROM threads WHERE oauth_user_id = %s ORDER BY updated_at DESC",
                    (oauth_user_id,),
                )
                rows = await cur.fetchall()
                return [
                    {"id": r["id"], "title": r["title"], "updated_at": r["updated_at"].isoformat()}  # type: ignore[call-overload]
                    for r in rows
                ]
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise


async def delete_thread_and_checkpoint(thread_id: str, oauth_user_id: str) -> None:
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM threads WHERE id = %s AND oauth_user_id = %s",
                    (thread_id, oauth_user_id),
                )
                for table in ("checkpoints", "checkpoint_writes", "checkpoint_blobs"):
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (thread_id,))
                    except Exception:
                        pass
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise
        