from typing import List
from src.config.db_pool import get_pool, reset_pool

async def get_selected_calendars(user_id: str) -> List[str]:
    """Return the calendar IDs the user has chosen to include. Defaults to ['primary']
    if they've never configured a preference — safe fallback for existing users."""
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT selected_calendar_ids FROM calendar_preferences WHERE user_id = %s",
                    (user_id,),
                )
                row = await cur.fetchone()
                if row:
                    return list(row["selected_calendar_ids"])  # type: ignore[index]
                return ["primary"]
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            return ["primary"]

async def set_selected_calendars(user_id: str, calendar_ids: List[str]) -> None:
    """Persist the user's chosen calendar IDs. Called when they toggle calendars in the UI."""
    for attempt in (1, 2):
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO calendar_preferences (user_id, selected_calendar_ids, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (user_id) DO UPDATE
                        SET selected_calendar_ids = EXCLUDED.selected_calendar_ids,
                            updated_at = now()
                    """,
                    (user_id, calendar_ids),
                )
            return
        except Exception:
            if attempt == 1:
                await reset_pool()
                continue
            raise