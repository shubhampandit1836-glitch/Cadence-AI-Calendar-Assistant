from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from src.middleware.require_session import require_session
from src.services.calendar_service import list_all_calendars
from src.repositories.calendar_preferences_repository import (
    get_selected_calendars,
    set_selected_calendars,
)

calendar_router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@calendar_router.get("")
async def get_calendars(auth=Depends(require_session)):
    """Return all writable calendars plus which ones are selected.
    Returns an empty list gracefully if the Google token is expired — the frontend
    hides the picker when disconnected, so this never reaches the UI in that state."""
    try:
        all_cals = list_all_calendars(auth["oauth_user_id"])
        selected = await get_selected_calendars(auth["user_id"])
        for cal in all_cals:
            cal["selected"] = cal["id"] in selected
        return {"calendars": all_cals, "selected": selected}
    except Exception as e:
        print(f"[GET /calendars Error] {e}")
        # Don't 500 — the token may simply be expired; the connection panel
        # will show disconnected and the picker will be hidden by the frontend.
        return {"calendars": [], "selected": ["primary"]}


class SelectCalendarsRequest(BaseModel):
    calendar_ids: List[str]


@calendar_router.post("/select")
async def select_calendars(body: SelectCalendarsRequest, auth=Depends(require_session)):
    """Persist which calendar IDs the agent should read from and write to."""
    try:
        if not body.calendar_ids:
            raise ValueError("At least one calendar must be selected.")
        await set_selected_calendars(auth["user_id"], body.calendar_ids)
        return {"selected": body.calendar_ids}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[POST /calendars/select Error] {e}")
        raise HTTPException(status_code=500, detail="Could not save your calendar preferences.")