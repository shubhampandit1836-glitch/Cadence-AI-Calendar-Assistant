import os
from typing import Any, Dict
import requests

def get_calendar_access_token(oauth_user_id: str) -> str:
    project_id = os.getenv("DESCOPE_PROJECT_ID", "").strip()
    management_key = os.getenv("DESCOPE_MANAGEMENT_KEY", "").strip()
    app_id = os.getenv("DESCOPE_CALENDAR_CONNECTION_ID", "google-calendar").strip()

    if not management_key or not project_id:
        raise ValueError("DESCOPE credentials are not properly configured in .env.")

    headers = {
        "Authorization": f"Bearer {project_id}:{management_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "appId": app_id,
        "userId": oauth_user_id,
        "options": {"withRefreshToken": False, "forceRefresh": False},
    }

    r = requests.post(
        "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest",
        json=payload, headers=headers, timeout=10
    )

    if not r.ok:
        print(f"[Descope Token Error]: User {oauth_user_id} - {r.status_code}: {r.text}")
        raise ValueError("Calendar access token not found. Please connect your Google Calendar.")

    data: Dict[str, Any] = r.json()
    access_token = (data.get("token") or {}).get("accessToken")

    if not access_token:
        raise ValueError("Failed to retrieve valid access token from Descope provider.")

    return str(access_token)