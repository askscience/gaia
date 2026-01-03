from .base import get_calendar_proxy, find_calendar_uid_by_name
from gi.repository import GLib

def remove_event(event_uid, calendar_uid=None, calendar_name=None, rid=""):
    """
    Removes an event from the specified calendar.
    rid is the Recurrence-ID, empty for single events.
    """
    target_uid = calendar_uid
    
    if not target_uid and calendar_name:
        target_uid = find_calendar_uid_by_name(calendar_name)
    
    if not target_uid:
        target_uid = 'system-calendar'

    try:
        cal_proxy = get_calendar_proxy(target_uid)
        
        # RemoveObjects signature: (a(ss)su)
        # uid_rid_array (a(ss)), mod_type (s), opflags (u)
        
        mod_type = "this"
        opflags = 0
        
        # Construct array of (uid, rid) tuples
        uid_rid_array = [(event_uid, rid)]
        
        cal_proxy.RemoveObjects('(a(ss)su)', uid_rid_array, mod_type, opflags)
        print(f"Successfully removed event {event_uid} from calendar {target_uid}")
        return True
    except Exception as e:
        print(f"Error removing event: {e}")
        return False
