from psycopg2.extras import RealDictCursor # type: ignore[reportMissingModuleSource]
from src.db.pool import get_connection, release_connection

def ensure_user(oauth_user_id: str, email: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (oauth_user_id, email)
                VALUES (%s, %s)
                ON CONFLICT (oauth_user_id)
                DO UPDATE SET email = COALESCE(EXCLUDED.email, users.email)
                RETURNING id, oauth_user_id, email, created_at;
                """,
                (oauth_user_id, email)
            )
            user = cur.fetchone()
            conn.commit()
            return dict(user) if user else {}
    finally:
        release_connection(conn)