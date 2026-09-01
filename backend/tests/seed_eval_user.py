"""Ensures the synthetic eval user exists in `users` before the eval suite runs, so
threads/user_memory/user_documents FK constraints (added in 007_identity_integrity.sql)
don't reject eval test writes. Idempotent — safe to run every time."""
import asyncio
from src.config.db_pool import get_pool

EVAL_OAUTH_USER_ID = "eval_test_user_do_not_use_for_real_data"

async def ensure_eval_user_exists():
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO users (oauth_user_id, email)
            VALUES (%s, %s)
            ON CONFLICT (oauth_user_id) DO NOTHING
            """,
            (EVAL_OAUTH_USER_ID, "eval-test-user@example.invalid"),
        )
    print(f"Ensured eval user exists: {EVAL_OAUTH_USER_ID}")

if __name__ == "__main__":
    asyncio.run(ensure_eval_user_exists())