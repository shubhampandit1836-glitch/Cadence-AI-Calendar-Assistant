from typing import Any, Dict, List, cast
from src.config.db_pool import get_pool


async def add_memory_fact(oauth_user_id: str, fact: str) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO user_memory (oauth_user_id, fact) VALUES (%s, %s)",
            (oauth_user_id, fact),
        )


async def get_recent_facts(oauth_user_id: str, limit: int = 8) -> List[str]:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT fact FROM user_memory WHERE oauth_user_id = %s ORDER BY created_at DESC LIMIT %s",
            (oauth_user_id, limit),
        )
        rows = cast(List[Dict[str, Any]], await cur.fetchall())
        return [r["fact"] for r in rows]