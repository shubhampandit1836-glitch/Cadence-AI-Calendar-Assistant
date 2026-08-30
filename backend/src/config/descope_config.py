import os
from importlib import import_module

DescopeClient = import_module("descope").DescopeClient

project_id = os.getenv("DESCOPE_PROJECT_ID", "")
management_key = os.getenv("DESCOPE_MANAGEMENT_KEY", "")

descope_client = None
if project_id:
    descope_client = DescopeClient(
        project_id=project_id,
        management_key=management_key if management_key else None
    )

CALENDAR_CONNECTION_ID = os.getenv("DESCOPE_CALENDAR_CONNECTION_ID", "google-calendar")
CALENDAR_CONNECTION_LABEL = "Google Calendar"