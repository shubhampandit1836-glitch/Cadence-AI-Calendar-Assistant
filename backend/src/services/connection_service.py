import os
from typing import Any, Dict, Optional
import requests
from src.config.descope_config import CALENDAR_CONNECTION_ID, CALENDAR_CONNECTION_LABEL
from src.repositories.connection_repository import (
    get_calendar_connection_row,
    upsert_calendar_connection,
)

def get_calendar_connection(user_id: str) -> Dict[str, Any]:
    row = get_calendar_connection_row(user_id)
    return {
        "label": CALENDAR_CONNECTION_LABEL,
        "status": row["status"] if row else "disconnected"
    }

def create_calendar_connect_url(
    user_id: str,
    oauth_user_id: str,
    session_token: str,
    refresh_token: Optional[str],
    redirect_url: str
) -> Dict[str, Any]:
    project_id = os.getenv("DESCOPE_PROJECT_ID", "").strip()
    app_id = os.getenv("DESCOPE_CALENDAR_CONNECTION_ID", "google-calendar").strip()

    if not project_id:
        raise ValueError("DESCOPE_PROJECT_ID is not configured in .env.")
    if not refresh_token:
        raise ValueError("Missing refresh token. Please sign out and sign back in, then try connecting again.")

    url = "https://api.descope.com/v1/outbound/oauth/connect"
    headers = {
        "Authorization": f"Bearer {project_id}:{refresh_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "appId": app_id,
        "options": {
            "redirectUrl": redirect_url,
        },
    }

    r = requests.post(url, json=payload, headers=headers, timeout=10)
    if not r.ok:
        print(f"[Descope Connect Error] {r.status_code}: {r.text}")
        raise ValueError(f"Could not initialize Descope outbound calendar connection: {r.status_code}: {r.text}")

    data = r.json()
    connect_url = data.get("url")
    if not connect_url:
        raise ValueError(f"Descope did not return a connect URL: {data}")

    upsert_calendar_connection(user_id, "pending")
    return {"url": connect_url}

def refresh_calendar_connection(user_id: str, oauth_user_id: str) -> Dict[str, Any]:
    project_id = os.getenv("DESCOPE_PROJECT_ID", "").strip()
    management_key = os.getenv("DESCOPE_MANAGEMENT_KEY", "").strip()
    app_id = os.getenv("DESCOPE_CALENDAR_CONNECTION_ID", "google-calendar").strip()

    headers = {
        "Authorization": f"Bearer {project_id}:{management_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "appId": app_id,
        "userId": oauth_user_id,
        "options": {"withRefreshToken": False, "forceRefresh": False},
    }

    try:
        r = requests.post(
            "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest",
            json=payload, headers=headers, timeout=10
        )
        access_token = None
        if r.ok:
            access_token = (r.json().get("token") or {}).get("accessToken")

        status = "connected" if access_token else "disconnected"
        upsert_calendar_connection(user_id, status)
        return {"label": CALENDAR_CONNECTION_LABEL, "status": status}
    except Exception as e:
        print(f"[Descope Refresh Error] {e}")
        upsert_calendar_connection(user_id, "disconnected")
        return {"label": CALENDAR_CONNECTION_LABEL, "status": "disconnected"}