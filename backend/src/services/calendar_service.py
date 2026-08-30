import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from src.services.token_service import get_calendar_access_token


def get_google_calendar_client(oauth_user_id: str) -> Any:
    token = get_calendar_access_token(oauth_user_id)
    credentials = Credentials(token=token)
    return build("calendar", "v3", credentials=credentials)


def format_event(event: Dict[str, Any]) -> Dict[str, Any]:
    reminders_raw = event.get("reminders", {})
    if reminders_raw.get("useDefault"):
        reminders_summary = "default (30 min popup)"
    elif reminders_raw.get("overrides"):
        parts = []
        for r in reminders_raw["overrides"]:
            mins = r.get("minutes", 0)
            method = r.get("method", "popup")
            if mins >= 60 and mins % 60 == 0:
                parts.append(f"{mins // 60}h {method}")
            else:
                parts.append(f"{mins}min {method}")
        reminders_summary = ", ".join(parts)
    else:
        reminders_summary = "none"

    return {
        "id": event.get("id", ""),
        # If set, this instance belongs to a recurring series and this is the master
        # event's ID. Deleting THIS id (not the instance id) cancels the whole series
        # in one call instead of deleting occurrences one at a time forever.
        "recurring_event_id": event.get("recurringEventId"),
        "title": event.get("summary", "Untitled Event"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", ""),
        "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date", ""),
        "hangoutLink": event.get("hangoutLink") or (
            event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")
        ),
        "attendees": [
            {"email": a.get("email"), "responseStatus": a.get("responseStatus")}
            for a in event.get("attendees", [])
        ],
        "reminders": reminders_summary,
    }


def get_primary_calendar_timezone(oauth_user_id: str) -> str:
    try:
        calendar = get_google_calendar_client(oauth_user_id)
        cal = calendar.calendars().get(calendarId="primary").execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"


def list_all_calendars(oauth_user_id: str) -> List[Dict[str, Any]]:
    """List every writable calendar in the user's Google account."""
    try:
        calendar = get_google_calendar_client(oauth_user_id)
        result = calendar.calendarList().list().execute()
        items = result.get("items", [])
        return [
            {
                "id": c["id"],
                "name": c.get("summary", c["id"]),
                "primary": c.get("primary", False),
                "accessRole": c.get("accessRole", "reader"),
                "backgroundColor": c.get("backgroundColor", "#4285f4"),
            }
            for c in items
            if c.get("accessRole") in ("owner", "writer")
        ]
    except Exception as e:
        print(f"[Calendar List Error] {e}")
        return []


def list_upcoming_meetings(
    oauth_user_id: str,
    max_results: int = 10,
    today_only: bool = False,
    calendar_id: str = "primary",
) -> List[Dict[str, Any]]:
    calendar = get_google_calendar_client(oauth_user_id)
    time_min = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    time_max: Optional[str] = None

    if today_only:
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        time_min = start.isoformat().replace("+00:00", "Z")
        time_max = end.isoformat().replace("+00:00", "Z")

    events_result = calendar.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    items = events_result.get("items", [])
    return [format_event(e) for e in items]


def list_upcoming_meetings_multi(
    oauth_user_id: str,
    calendar_ids: List[str],
    max_results: int = 10,
    today_only: bool = False,
) -> List[Dict[str, Any]]:
    """List upcoming meetings across multiple calendars, merged and deduplicated."""
    all_events: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for cal_id in calendar_ids:
        try:
            events = list_upcoming_meetings(
                oauth_user_id,
                max_results=max_results,
                today_only=today_only,
                calendar_id=cal_id,
            )
            for e in events:
                if e["id"] not in seen_ids:
                    seen_ids.add(e["id"])
                    e["calendar_id"] = cal_id
                    all_events.append(e)
        except Exception as ex:
            print(f"[Multi-Calendar List Error] cal={cal_id} {ex}")

    all_events.sort(key=lambda x: x.get("start", ""))
    return all_events[:max_results]


def check_calendar_busy(
    oauth_user_id: str,
    start_iso: str,
    end_iso: str,
    calendar_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Check free/busy across every calendar in `calendar_ids` (defaults to just the
    user's primary calendar if none are supplied). Previously this always queried only
    'primary', silently ignoring any secondary calendars the user had selected in the app."""
    ids = calendar_ids or ["primary"]
    calendar = get_google_calendar_client(oauth_user_id)
    body = {
        "timeMin": start_iso,
        "timeMax": end_iso,
        "items": [{"id": cid} for cid in ids],
    }
    result = calendar.freebusy().query(body=body).execute()
    calendars = result.get("calendars", {})
    busy_slots: List[Dict[str, str]] = []
    for cid in ids:
        for slot in calendars.get(cid, {}).get("busy", []):
            busy_slots.append({"start": slot.get("start"), "end": slot.get("end"), "calendar_id": cid})
    return {
        "is_busy": len(busy_slots) > 0,
        "busy_slots": busy_slots,
    }


def create_meeting(
    oauth_user_id: str,
    title: str,
    start_iso: str,
    end_iso: str,
    attendee_emails: Optional[List[str]] = None,
    description: str = "",
    add_google_meet: bool = True,
    recurrence_rule: Optional[str] = None,
    calendar_id: str = "primary",
    reminders: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """reminders format: [{"method": "email"|"popup", "minutes": int}]
    e.g. [{"method": "popup", "minutes": 10}, {"method": "email", "minutes": 60}]
    Pass an empty list [] to disable all reminders. Pass None to use Google's default."""
    calendar = get_google_calendar_client(oauth_user_id)
    tz = get_primary_calendar_timezone(oauth_user_id)
    safe_emails: List[str] = attendee_emails if attendee_emails is not None else []

    body: Dict[str, Any] = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
        "attendees": [{"email": email} for email in safe_emails],
    }

    if recurrence_rule:
        body["recurrence"] = [recurrence_rule]

    if reminders is not None:
        # useDefault=False + explicit overrides = custom reminders
        # useDefault=False + empty list = no reminders at all
        body["reminders"] = {
            "useDefault": False,
            "overrides": reminders,
        }
    else:
        # useDefault=True = Google's default (usually a 30-min popup)
        body["reminders"] = {"useDefault": True}

    if add_google_meet:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    event = calendar.events().insert(
        calendarId=calendar_id,
        sendUpdates="all",
        conferenceDataVersion=1 if add_google_meet else 0,
        body=body,
    ).execute()

    return format_event(event)

def reschedule_meeting(
    oauth_user_id: str,
    event_id: str,
    start_iso: str,
    end_iso: str,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    calendar = get_google_calendar_client(oauth_user_id)
    tz = get_primary_calendar_timezone(oauth_user_id)
    body = {
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
    }
    event = calendar.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        sendUpdates="all",
        body=body,
    ).execute()
    return format_event(event)


def cancel_meeting(
    oauth_user_id: str,
    event_id: str,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    calendar = get_google_calendar_client(oauth_user_id)
    calendar.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
        sendUpdates="all",
    ).execute()
    return {"success": True, "event_id": event_id}


def cancel_all_upcoming_meetings(oauth_user_id: str, calendar_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Cancel every upcoming meeting across every calendar in `calendar_ids` (defaults
    to just 'primary'). Handles recurring series correctly: instead of deleting the next
    N individual occurrences one at a time (which never catches up with an unbounded
    weekly series — the next batch just regenerates further in the future), this deletes
    each distinct recurring series' MASTER event once, cancelling all of its past and
    future occurrences in a single call. Non-recurring events are cancelled individually
    as before."""
    ids = calendar_ids or ["primary"]
    if len(ids) > 1:
        events = list_upcoming_meetings_multi(oauth_user_id, ids, max_results=100)
    else:
        events = list_upcoming_meetings(oauth_user_id, max_results=100, calendar_id=ids[0])
        for e in events:
            e["calendar_id"] = ids[0]

    # Collapse recurring instances down to one delete-target per series (the master
    # event id), keyed by (calendar_id, master_id) so the same series on two calendars
    # is still handled once per calendar. Non-recurring events delete by their own id.
    targets: Dict[tuple, Dict[str, Any]] = {}
    for e in events:
        cal_id = e.get("calendar_id", "primary")
        master_id = e.get("recurring_event_id") or e["id"]
        key = (cal_id, master_id)
        if key not in targets:
            targets[key] = {"id": master_id, "calendar_id": cal_id, "title": e.get("title", master_id)}

    cancelled, failed = [], []
    for target in targets.values():
        try:
            cancel_meeting(oauth_user_id, event_id=target["id"], calendar_id=target["calendar_id"])
            cancelled.append(target["title"])
        except Exception as err:
            failed.append({"title": target["title"], "error": str(err)})
    return {"cancelled_count": len(cancelled), "cancelled": cancelled, "failed": failed}


def find_events_by_query(
    oauth_user_id: str, query: str, max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search upcoming events by title/description substring match."""
    events = list_upcoming_meetings(oauth_user_id, max_results=50)
    q = query.lower().strip()
    matches = [
        e for e in events
        if q in e.get("title", "").lower() or q in e.get("description", "").lower()
    ]
    return matches[:max_results]