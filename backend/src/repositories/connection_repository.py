from typing import Any, Dict, Optional
from psycopg2.extras import RealDictCursor  # type: ignore[reportMissingModuleSource]
from src.db.pool import get_connection, release_connection

def get_calendar_connection_row(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id, provider, status, updated_at
                FROM connections
                WHERE user_id = %s AND provider = 'calendar';
                """,
                (user_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)

def upsert_calendar_connection(user_id: str, status: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO connections (user_id, provider, status, updated_at)
                VALUES (%s, 'calendar', %s, NOW())
                ON CONFLICT (user_id, provider)
                DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()
                RETURNING user_id, provider, status, updated_at;
                """,
                (user_id, status)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}
    finally:
        release_connection(conn)