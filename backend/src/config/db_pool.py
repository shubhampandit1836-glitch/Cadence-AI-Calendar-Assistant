import os
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    open=False,
    min_size=2,
    max_size=20,
    reconnect_timeout=10,
    max_waiting=50,
    timeout=30,
    kwargs={"autocommit": True, "row_factory": dict_row},
)
        await _pool.open()
    return _pool


async def reset_pool() -> None:
    """Force the pool (and checkpointer) to rebuild on next use. Call this right after any DB
    error so the app recovers within the same request instead of waiting on internal pool timers."""
    global _pool, _checkpointer
    old_pool = _pool
    _pool = None
    _checkpointer = None
    if old_pool is not None:
        try:
            await old_pool.close()
        except Exception:
            pass


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        pool = await get_pool()
        _checkpointer = AsyncPostgresSaver(pool) # type: ignore[arg-type]
        await _checkpointer.setup()
    return _checkpointer