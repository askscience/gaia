from src.tools.base import BaseTool
from src.tools.calendar.add_event import add_event
from src.tools.calendar.remove_event import remove_event
from src.tools.calendar.create_calendar import create_calendar
from src.tools.calendar.list_events import list_events
from src.tools.calendar.list_calendars import list_calendars
import datetime

class AddEventTool(BaseTool):
    @property
    def name(self) -> str:
        return "calendar_add_event"

    @property
    def description(self) -> str:
        return "Add an event to the GNOME Calendar. Returns the UUID of the created event."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "The title or summary of the event."
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (e.g., '2023-10-27T10:00:00')"},
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO 8601 format (e.g., '2023-10-27T11:00:00')"
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar to add the event to. Defaults to system/personal calendar if omitted."
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the event."
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }

    def execute(self, summary, start_time, end_time, calendar_name=None, description="", **kwargs):
        # Parse times. The AI usually sends ISO strings.
        try:
            # Flexible parsing (handling potential Z or T)
            # For simplicity assuming isoformat
            dt_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            dt_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            return "Error: Invalid date format. Please use ISO 8601 (e.g. 2023-10-27T10:00:00)"

        result = add_event(summary, dt_start, dt_end, calendar_name=calendar_name, description=description)
        if result:
            return f"Event added successfully. UUID: {result}"
        else:
            return "Failed to add event."

class RemoveEventTool(BaseTool):
    @property
    def name(self) -> str:
        return "calendar_remove_event"

    @property
    def description(self) -> str:
        return "Remove an event from the GNOME Calendar using its UUID."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "event_uid": {
                    "type": "string",
                    "description": "The UUID of the event to remove."
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar the event belongs to."
                }
            },
            "required": ["event_uid"]
        }

    def execute(self, event_uid, calendar_name=None, **kwargs):
        success = remove_event(event_uid, calendar_name=calendar_name)
        if success:
            return f"Event {event_uid} removed successfully."
        else:
            return f"Failed to remove event {event_uid}."

class CreateCalendarTool(BaseTool):
    @property
    def name(self) -> str:
        return "calendar_create"

    @property
    def description(self) -> str:
        return "Create a new local calendar in GNOME Calendar."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Display name for the new calendar."
                },
                "color": {
                    "type": "string",
                    "description": "Color for the calendar (hex format, e.g. #ff0000). Default is green."
                }
            },
            "required": ["name"]
        }

    def execute(self, name, color="#2ec27e", **kwargs):
        uid = create_calendar(name, color)
        if uid:
            return f"Calendar '{name}' created successfully with UID {uid}."
        else:
            return f"Failed to create calendar '{name}'."

class ListEventsTool(BaseTool):
    @property
    def name(self) -> str:
        return "calendar_list_events"

    @property
    def description(self) -> str:
        return "List events from the GNOME Calendar. Useful for finding event UIDs by date or description."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date/time in ISO 8601 format (e.g., '2023-10-27T00:00:00') to filter events starting after this time."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date/time in ISO 8601 format to filter events ending before this time."
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar to list events from."
                }
            }
        }

    def execute(self, start_date=None, end_date=None, calendar_name=None, **kwargs):
        dt_start = None
        dt_end = None
        
        try:
            if start_date:
                dt_start = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                dt_end = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
             return "Error: Invalid date format. Please use ISO 8601."
             
        events = list_events(dt_start, dt_end, calendar_name=calendar_name)
        
        if not events:
            return "No events found."
            
        # Format for AI
        result = [f"Found {len(events)} events:"]
        for e in events:
            result.append(f"- UID: {e.get('uid', 'N/A')}")
            result.append(f"  Summary: {e.get('summary', 'No Title')}")
            result.append(f"  Start: {e.get('start', 'N/A')}")
            result.append(f"  End: {e.get('end', 'N/A')}")
            result.append("")
            
        return "\n".join(result)

class ListCalendarsTool(BaseTool):
    @property
    def name(self) -> str:
        return "calendar_list_sources"

    @property
    def description(self) -> str:
        return "List all available calendars with their UIDs and Names. Use this to find the correct calendar_name for other tools."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self, **kwargs):
        calendars = list_calendars()
        if not calendars:
            return "No calendars found."
            
        result = ["Available Calendars:"]
        for c in calendars:
            result.append(f"- Name: {c['name']}")
            result.append(f"  UID: {c['uid']}")
            result.append(f"  Color: {c['color']}")
            result.append("")
            
        return "\n".join(result)
