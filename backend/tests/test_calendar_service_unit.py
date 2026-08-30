"""Mocked unit tests for calendar_service — pin the check_calendar_busy multi-calendar
fix so it never regresses back to hardcoding 'primary'."""
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from src.services import calendar_service


class FakeFreebusy:
    def __init__(self, response):
        self._response = response
        self.last_body: Dict[str, Any] = {}

    def query(self, body):
        self.last_body = body
        return MagicMock(execute=MagicMock(return_value=self._response))


class FakeCalendarClient:
    def __init__(self, response):
        self.freebusy_obj = FakeFreebusy(response)

    def freebusy(self):
        return self.freebusy_obj


def test_check_calendar_busy_defaults_to_primary_when_no_calendar_ids_given():
    response = {
        "calendars": {
            "primary": {"busy": [{"start": "2026-01-01T10:00:00Z", "end": "2026-01-01T11:00:00Z"}]}
        }
    }
    fake_client = FakeCalendarClient(response)
    with patch.object(calendar_service, "get_google_calendar_client", return_value=fake_client):
        result = calendar_service.check_calendar_busy(
            "user-1", "2026-01-01T09:00:00Z", "2026-01-01T12:00:00Z"
        )

    assert fake_client.freebusy_obj.last_body["items"] == [{"id": "primary"}]
    assert result["is_busy"] is True
    assert result["busy_slots"][0]["calendar_id"] == "primary"


def test_check_calendar_busy_queries_every_selected_calendar():
    response = {
        "calendars": {
            "primary": {"busy": []},
            "work@example.com": {
                "busy": [{"start": "2026-01-01T10:00:00Z", "end": "2026-01-01T10:30:00Z"}]
            },
        }
    }
    fake_client = FakeCalendarClient(response)
    with patch.object(calendar_service, "get_google_calendar_client", return_value=fake_client):
        result = calendar_service.check_calendar_busy(
            "user-1",
            "2026-01-01T09:00:00Z",
            "2026-01-01T12:00:00Z",
            calendar_ids=["primary", "work@example.com"],
        )

    assert fake_client.freebusy_obj.last_body["items"] == [
        {"id": "primary"},
        {"id": "work@example.com"},
    ]
    assert result["is_busy"] is True
    assert result["busy_slots"][0]["calendar_id"] == "work@example.com"


def test_check_calendar_busy_not_busy_when_no_slots_returned():
    response = {"calendars": {"primary": {"busy": []}}}
    fake_client = FakeCalendarClient(response)
    with patch.object(calendar_service, "get_google_calendar_client", return_value=fake_client):
        result = calendar_service.check_calendar_busy(
            "user-1", "2026-01-01T09:00:00Z", "2026-01-01T12:00:00Z"
        )

    assert result["is_busy"] is False
    assert result["busy_slots"] == []