from .base import get_calendar_proxy, find_calendar_uid_by_name
import datetime

def list_events(start_date=None, end_date=None, calendar_uid=None, calendar_name=None):
    """
    Lists events from a calendar.
    
    start_date and end_date should be datetime objects.
    If provided, filters events occurring in that range.
    If not provided, lists all events (or a default limit if backend enforces one, but EDS usually returns all).
    
    Returns a list of event dictionaries with 'uid', 'summary', 'start', 'end', 'description'.
    The raw output from EDS is a list of iCalendar strings. We will parse them simply.
    """
    
    target_uid = calendar_uid
    
    if not target_uid and calendar_name:
        target_uid = find_calendar_uid_by_name(calendar_name)
    
    if not target_uid:
        # Fallback to 'system-calendar'
        target_uid = 'system-calendar'

    try:
        cal_proxy = get_calendar_proxy(target_uid)
        
        # Construct Query
        # EDS uses S-Expressions.
        # Queries that worked in debug_list: 
        # (contains? "summary" "") found 0 (empty result but valid)
        # (exists? "uid") failed.
        # According to Gnome docs, to get all objects, one often uses widely matching queries.
        # let's try (contains? "summary" "") as it worked in debug_list.
        query = '(contains? "summary" "")'
        
        if start_date and end_date:
             # If explicit dates, try time range, but be careful of format.
             # Using simpler existence check first to verify base functionality.
             s_iso = start_date.strftime('%Y%m%dT%H%M%SZ')
             e_iso = end_date.strftime('%Y%m%dT%H%M%SZ')
             query = f'(occur-in-time-range? (make-time "{s_iso}") (make-time "{e_iso}"))'
        
        # GetObjectList signature: (s) -> (as)
        # s: query
        # out: as (array of strings, where each string is an iCal component)
        
        result = cal_proxy.GetObjectList('(s)', query)
        if not result or len(result) == 0:
            return []
            
        # PyGObject / GDBus often returns the result directly. 
        # If the result is a list of strings, we iterate it.
        # If it happens to be wrapped in a tuple (as), we check.
        
        ics_list = result
        if isinstance(result, tuple):
             ics_list = result[0]
        
        parsed_events = []
        for ics in ics_list:
            # EDS returns individual component string e.g. "BEGIN:VEVENT..."
            # My parser split lines but might need better newline handling
            # because EDS might return \r\n
            event = parse_ical_event(ics)
            if event:
                parsed_events.append(event)
                
        return parsed_events

    except Exception as e:
        print(f"Error listing events: {e}")
        return []

def parse_ical_event(ics_string):
    """
    Simple parser to extract key fields from a VEVENT string.
    """
    event = {}
    # Handle potentially escaped newlines from DBus/GVariant
    # Replace literal \r\n and \n with actual newline
    raw_text = ics_string.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\r\n', '\n')
    lines = raw_text.split('\n')
        
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if ':' in line:  # Basic property parsing
             # Be careful with lines like "DESCRIPTION:foo:bar"
             parts = line.split(':', 1)
             key_raw = parts[0]
             val = parts[1]
             
             # Remove params
             key = key_raw.split(';')[0].upper()
        
             # Handling generic fields for robust basic data extraction
             if key == 'UID': 
                 event['uid'] = val.strip()
             elif key == 'SUMMARY': event['summary'] = val.strip()
             elif key.startswith('DESCRIPTION'): event['description'] = val.strip()
             elif key.startswith('DTSTART'): event['start'] = val.strip()
             elif key.startswith('DTEND'): event['end'] = val.strip()
            
    # Normalize if needed
    return event
