import json
from typing import Any, Dict
from src.services.calendar_service import list_upcoming_meetings, check_calendar_busy, find_events_by_query

MCP_CALENDAR_TOOLS = [
    {
        "name": "list_upcoming_meetings",
        "description": "List upcoming Google Calendar events for the authenticated user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "maxResults": {"type": "number", "description": "Max results to return"},
                "todayOnly": {"type": "boolean", "description": "Fetch today's events only"},
            },
        },
    },
    {
        "name": "check_calendar_busy",
        "description": "Check free/busy status for the authenticated user's primary calendar in a time window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "startIso": {"type": "string", "description": "Start ISO timestamp"},
                "endIso": {"type": "string", "description": "End ISO timestamp"},
            },
            "required": ["startIso", "endIso"],
        },
    },
    {
        "name": "find_meeting_by_title",
        "description": "Search the authenticated user's upcoming meetings by title/description keywords.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keywords to search for"}},
            "required": ["query"],
        },
    },
]


def handle_mcp_tool_call(tool_name: str, oauth_user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """oauth_user_id must come from a validated Descope session (see mcp/mount.py) —
    never accept it from the request body, or one MCP client could read another user's
    calendar."""
    if tool_name == "list_upcoming_meetings":
        events = list_upcoming_meetings(
            oauth_user_id,
            max_results=arguments.get("maxResults", 10),
            today_only=arguments.get("todayOnly", False),
        )
        return {"content": [{"type": "text", "text": json.dumps(events, indent=2)}]}

    if tool_name == "check_calendar_busy":
        result = check_calendar_busy(
            oauth_user_id,
            start_iso=arguments["startIso"],
            end_iso=arguments["endIso"],
        )
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    if tool_name == "find_meeting_by_title":
        events = find_events_by_query(oauth_user_id, query=arguments["query"])
        return {"content": [{"type": "text", "text": json.dumps(events, indent=2)}]}

    raise ValueError(f"Tool {tool_name} not found.")