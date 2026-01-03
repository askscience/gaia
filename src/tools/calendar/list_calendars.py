from .base import get_source_manager_proxy, EDS_SOURCE_INTERFACE

def list_calendars():
    """
    Lists all available calendars.
    Returns a list of dictionaries containing 'uid', 'name', and 'color'.
    """
    try:
        source_manager = get_source_manager_proxy()
        # We need ObjectManager to iterate capabilities
        # Reuse logic from base finding or just create new proxy here as SourceManager usually implements ObjectManager
        
        # Actually base.py has get_source_manager_proxy returning the specific SourceManager interface proxy
        # But to list objects we need org.freedesktop.DBus.ObjectManager interface on the same path
        import gi
        from gi.repository import Gio
        
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        obj_manager = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.gnome.evolution.dataserver.Sources5',
            '/org/gnome/evolution/dataserver/SourceManager',
            'org.freedesktop.DBus.ObjectManager',
            None,
        )
        
        objects = obj_manager.GetManagedObjects()
        calendars = []
        
        for path, interfaces in objects.items():
            source = interfaces.get(EDS_SOURCE_INTERFACE)
            if source:
                data = source.get('Data', '')
                uid = source.get('UID')
                
                # Check if it is a calendar
                if '[Calendar]' in data:
                    name = "Unknown"
                    color = None
                    
                    # Parse keyfile data
                    # DisplayName=...
                    # Color=...
                    for line in data.splitlines():
                        if line.startswith('DisplayName='):
                            name = line.split('=', 1)[1]
                        elif line.startswith('Color='):
                            color = line.split('=', 1)[1]
                            
                    calendars.append({
                        'uid': uid,
                        'name': name,
                        'color': color
                    })
                    
        return calendars

    except Exception as e:
        print(f"Error listing calendars: {e}")
        return []
