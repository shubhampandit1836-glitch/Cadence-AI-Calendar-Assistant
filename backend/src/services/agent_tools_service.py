import json
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from src.services.calendar_service import (
    list_upcoming_meetings,
    list_upcoming_meetings_multi,
    list_all_calendars,
    check_calendar_busy,
    create_meeting,
    reschedule_meeting,
    cancel_meeting,
    find_events_by_query,
)
from src.services.rag_service import search_rag_context, remove_documents_by_name, remove_all_documents
from src.repositories.document_repository import list_user_documents
from src.repositories.calendar_preferences_repository import get_selected_calendars


class ListMeetingsInput(BaseModel):
    max_results: Optional[int] = Field(default=10, description="Max number of meetings to fetch")
    today_only: Optional[bool] = Field(default=False, description="Filter for today only")


class FindMeetingInput(BaseModel):
    query: str = Field(description="Title/topic keywords to search for")


class CheckBusyInput(BaseModel):
    start_iso: str = Field(description="Start time ISO string")
    end_iso: str = Field(description="End time ISO string")


class ReminderItem(BaseModel):
    method: str = Field(description="'popup' or 'email'")
    minutes: int = Field(description="Minutes before the event to trigger the reminder")

class CreateMeetingInput(BaseModel):
    title: str = Field(description="Meeting title")
    start_iso: str = Field(description="Start time ISO string with timezone offset")
    end_iso: str = Field(description="End time ISO string with timezone offset")
    attendee_emails: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(default="")
    add_google_meet: Optional[bool] = Field(default=True)
    recurrence_rule: Optional[str] = Field(default=None)
    calendar_id: Optional[str] = Field(
        default=None,
        description="Which calendar to create the event in. Omit to use the user's primary calendar.",
    )
    reminders: Optional[List[ReminderItem]] = Field(
        default=None,
        description=(
            "Custom reminders for the event. Each entry has 'method' ('popup' or 'email') and "
            "'minutes' (how many minutes before the event). Examples: "
            "[{'method': 'popup', 'minutes': 10}] for a 10-min popup, "
            "[{'method': 'email', 'minutes': 60}, {'method': 'popup', 'minutes': 5}] for both. "
            "Pass an empty list [] to create the event with NO reminders. "
            "Omit entirely to use Google's default reminder (30-min popup)."
        ),
    )


class RescheduleInput(BaseModel):
    event_id: str = Field(description="Event ID to reschedule")
    start_iso: str = Field(description="New start ISO string")
    end_iso: str = Field(description="New end ISO string")
    calendar_id: Optional[str] = Field(default=None, description="Calendar the event lives in (omit for primary)")


class CancelInput(BaseModel):
    event_id: str = Field(description="Event ID to cancel")
    calendar_id: Optional[str] = Field(default=None, description="Calendar the event lives in (omit for primary)")


class DeleteDocsInput(BaseModel):
    filename: Optional[str] = Field(default=None)
    delete_all: bool = Field(default=False)
    confirmed: bool = Field(default=False)


class SearchDocsInput(BaseModel):
    query: str = Field(description="Keywords or question about uploaded documents")
    filename: Optional[str] = Field(default=None)


class CancelAllInput(BaseModel):
    confirmed: bool = Field(default=False)


def get_calendar_tools_for_user(oauth_user_id: str, user_id: str):
    @tool("list_my_calendars")
    async def list_cals_tool() -> str:
        """List all Google Calendars in the user's account (name, id, whether currently selected).
        Use this when the user asks 'what calendars do I have', 'show my calendars', or wants
        to know which calendars Cadence is currently using."""
        try:
            cals = list_all_calendars(oauth_user_id)
            selected = await get_selected_calendars(user_id)
            for c in cals:
                c["selected"] = c["id"] in selected
            return json.dumps(cals)
        except Exception as e:
            return json.dumps({"error": f"Could not list calendars: {e}"})

    @tool("list_upcoming_meetings", args_schema=ListMeetingsInput)
    async def list_tool(max_results: Optional[int] = 10, today_only: Optional[bool] = False) -> str:
        """List upcoming meetings from the user's selected calendars."""
        try:
            selected = await get_selected_calendars(user_id)
            if len(selected) == 1 and selected[0] == "primary":
                res = list_upcoming_meetings(oauth_user_id, max_results=max_results or 10, today_only=bool(today_only))
            else:
                res = list_upcoming_meetings_multi(oauth_user_id, selected, max_results=max_results or 10, today_only=bool(today_only))
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not list meetings: {e}"})

    @tool("find_meeting_by_title", args_schema=FindMeetingInput)
    def find_tool(query: str) -> str:
        """Search upcoming meetings by title or description keywords."""
        try:
            res = find_events_by_query(oauth_user_id, query=query)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not search meetings: {e}"})

    @tool("check_calendar_busy", args_schema=CheckBusyInput)
    async def busy_tool(start_iso: str, end_iso: str) -> str:
        """Check if the user's calendar has conflicts during a time window."""
        try:
            selected = await get_selected_calendars(user_id)
            res = check_calendar_busy(oauth_user_id, start_iso=start_iso, end_iso=end_iso, calendar_ids=selected)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not check availability: {e}"})

    @tool("create_meeting", args_schema=CreateMeetingInput)
    def create_tool(
        title: str,
        start_iso: str,
        end_iso: str,
        attendee_emails: Optional[List[str]] = None,
        description: Optional[str] = "",
        add_google_meet: Optional[bool] = True,
        recurrence_rule: Optional[str] = None,
        calendar_id: Optional[str] = None,
        reminders: Optional[List[ReminderItem]] = None,
    ) -> str:
        """Create a new Google Calendar meeting. Supports attendees, Google Meet link,
        recurrence, a specific target calendar, and custom reminders (popup or email,
        at any number of minutes before the event). Omit reminders to use Google's default."""
        try:
            reminder_dicts = (
                [{"method": r.method, "minutes": r.minutes} for r in reminders]
                if reminders is not None else None
            )
            res = create_meeting(
                oauth_user_id,
                title=title,
                start_iso=start_iso,
                end_iso=end_iso,
                attendee_emails=attendee_emails or [],
                description=description or "",
                add_google_meet=True if add_google_meet is None else add_google_meet,
                recurrence_rule=recurrence_rule,
                calendar_id=calendar_id or "primary",
                reminders=reminder_dicts,
            )
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not create the meeting: {e}"})

    @tool("reschedule_meeting", args_schema=RescheduleInput)
    def reschedule_tool(event_id: str, start_iso: str, end_iso: str, calendar_id: Optional[str] = None) -> str:
        """Reschedule an existing meeting."""
        try:
            res = reschedule_meeting(oauth_user_id, event_id=event_id, start_iso=start_iso, end_iso=end_iso, calendar_id=calendar_id or "primary")
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not reschedule the meeting: {e}"})

    @tool("cancel_meeting", args_schema=CancelInput)
    def cancel_tool(event_id: str, calendar_id: Optional[str] = None) -> str:
        """Cancel and delete a calendar event."""
        try:
            res = cancel_meeting(oauth_user_id, event_id=event_id, calendar_id=calendar_id or "primary")
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not cancel the meeting: {e}"})

    @tool("cancel_all_upcoming_meetings", args_schema=CancelAllInput)
    async def cancel_all_tool(confirmed: bool = False) -> str:
        """Cancel every upcoming meeting. IRREVERSIBLE. First call must have confirmed=false."""
        import asyncio
        from src.services.calendar_service import cancel_all_upcoming_meetings
        selected = await get_selected_calendars(user_id)
        if not confirmed:
            from src.services.calendar_service import list_upcoming_meetings_multi, list_upcoming_meetings
            events = list_upcoming_meetings_multi(oauth_user_id, selected, max_results=100) if len(selected) > 1 else list_upcoming_meetings(oauth_user_id, max_results=100)
            return json.dumps({
                "needs_confirmation": True,
                "count": len(events),
                "titles": [e.get("title") for e in events],
                "message": f"This will cancel all {len(events)} upcoming meetings. Please confirm.",
            })
        try:
            # Run on a worker thread — this does up to 100 sequential blocking Google API
            # calls, and without to_thread it would freeze the entire single-process
            # event loop (every other request, for every user) until it finished.
            res = await asyncio.to_thread(cancel_all_upcoming_meetings, oauth_user_id, selected)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Could not cancel meetings: {e}"})

    @tool("list_uploaded_documents")
    async def list_docs_tool() -> str:
        """Return the authoritative list of currently uploaded work documents."""
        try:
            docs = await list_user_documents(oauth_user_id)
            if not docs:
                return json.dumps({"message": "No documents are currently uploaded."})
            return json.dumps([{"filename": d["filename"]} for d in docs])
        except Exception as e:
            return json.dumps({"error": f"Could not list documents: {e}"})

    @tool("delete_uploaded_documents", args_schema=DeleteDocsInput)
    async def delete_docs_tool(filename: Optional[str] = None, delete_all: bool = False, confirmed: bool = False) -> str:
        """Delete one or all uploaded documents. confirmed must be false on first call."""
        if not confirmed:
            target = "ALL uploaded documents" if delete_all else f'"{filename}"'
            return json.dumps({"needs_confirmation": True, "message": f"Please confirm you want to permanently delete {target}."})
        try:
            if delete_all:
                count = await remove_all_documents(oauth_user_id)
                return json.dumps({"deleted_count": count})
            if not filename:
                return json.dumps({"error": "No filename provided."})
            await remove_documents_by_name(oauth_user_id, filename)
            return json.dumps({"deleted": filename})
        except Exception as e:
            return json.dumps({"error": f"Could not delete document(s): {e}"})

    @tool("search_uploaded_documents", args_schema=SearchDocsInput)
    async def rag_search_tool(query: str, filename: Optional[str] = None) -> str:
        """Search uploaded work documents for content relevant to a question."""
        try:
            results = await search_rag_context(oauth_user_id, query=query, top_k=3, filename=filename)
            if not results:
                return json.dumps({"message": "No relevant document passages found."})
            return json.dumps(results)
        except Exception as e:
            return json.dumps({"error": f"Document search failed: {e}"})

    return [
        list_cals_tool, list_tool, find_tool, busy_tool, create_tool,
        reschedule_tool, cancel_tool, cancel_all_tool,
        list_docs_tool, delete_docs_tool, rag_search_tool,
    ]