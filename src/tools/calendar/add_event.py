from .base import get_calendar_proxy, find_calendar_uid_by_name
import datetime
import uuid

def generate_ical_string(uid, summary, start_time, end_time, description=""):
    """
    Generates a simple VEVENT iCalendar string.
    start_time and end_time should be datetime objects.
    """
    # Format dates as YYYYMMDDTHHMMSSZ
    # Ensure UTC or handle timezone. For simplicity, we'll assume naive times are local or handle as floating
    # But EDS usually prefers UTC.
    
    dtstamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dtstart = start_time.strftime('%Y%m%dT%H%M%SZ')
    dtend = end_time.strftime('%Y%m%dT%H%M%SZ')
    
    ical = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "END:VEVENT"
    ]
    return "\r\n".join(ical)

def add_event(summary, start_time, end_time, calendar_uid=None, calendar_name=None, description=""):
    """
    Adds an event to the specified calendar.
    """
    target_uid = calendar_uid
    
    if not target_uid and calendar_name:
        target_uid = find_calendar_uid_by_name(calendar_name)
    
    if not target_uid:
        # Fallback to 'system-calendar' or 'personal' if neither specified
        # or error out. Let's try 'personal' (often 'system-calendar-local' or source_10 etc)
        # But 'system-calendar' seemed to work in introspection.
        target_uid = 'system-calendar'

    try:
        cal_proxy = get_calendar_proxy(target_uid)
        
        # Generate UID here so we can return it
        uid = str(uuid.uuid4())
        
        ical_string = generate_ical_string(uid, summary, start_time, end_time, description)
        
        # CreateObjects signature is (asu) -> (as)
        # ics_objects (as), opflags (u)
        opflags = 0
        
        # We need to pass the signature for the call
        result = cal_proxy.CreateObjects('(asu)', [ical_string], opflags)
        
        # Result is (uids,) - tuple containing list of uids
        uids = result[0]
        if uids:
            # The result uids[0] might be an internal ID (e.g. "1", "2") for local backend
            # while the actual UID in the iCal data is the one we generated.
            # RemoveObjects usually requires the iCal UID.
            # So we return the generated uid.
            print(f"Successfully added event '{summary}' to calendar {target_uid}. Internal ID: {uids[0]}, UUID: {uid}")
            return uid
        return None
    except Exception as e:
        print(f"Error adding event: {e}")
        return None
