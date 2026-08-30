from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from src.middleware.require_session import require_session
from src.services.connection_service import (
    get_calendar_connection,
    create_calendar_connect_url,
    refresh_calendar_connection
)

connection_router = APIRouter(prefix="/api/connections", tags=["connections"])

class ConnectRequest(BaseModel):
    refreshToken: Optional[str] = None
    redirectUrl: Optional[str] = None

@connection_router.get("")
@connection_router.get("/")
async def get_connection_status(auth=Depends(require_session)):
    try:
        res = get_calendar_connection(auth["user_id"])
        return {"connection": res}
    except Exception as e:
        print(f"[GET /connections Error] {e}")
        raise HTTPException(status_code=500, detail="Could not load your connection status. Please try again.")

@connection_router.post("/connect")
async def connect(
    body: ConnectRequest,
    authorization: Optional[str] = Header(None),
    auth=Depends(require_session)
):
    try:
        session_token = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
        redirect_url = body.redirectUrl or "http://localhost:3000/dashboard"

        res = create_calendar_connect_url(
            user_id=auth["user_id"],
            oauth_user_id=auth["oauth_user_id"],
            session_token=session_token,
            refresh_token=body.refreshToken,
            redirect_url=redirect_url
        )
        return res
    except Exception as e:
        print(f"[POST /connections/connect Error] {e}")
        raise HTTPException(status_code=500, detail="Could not start the calendar connection. Please try again.")

@connection_router.post("/refresh-status")
async def refresh_status(auth=Depends(require_session)):
    try:
        res = refresh_calendar_connection(auth["user_id"], auth["oauth_user_id"])
        return {"connection": res}
    except Exception as e:
        print(f"[POST /connections/refresh-status Error] {e}")
        raise HTTPException(status_code=500, detail="Could not refresh your connection status. Please try again.")