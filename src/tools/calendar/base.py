import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

# Constants for Evolution Data Server
EDS_CALENDAR_BUS_NAME = 'org.gnome.evolution.dataserver.Calendar8'
EDS_CALENDAR_FACTORY_PATH = '/org/gnome/evolution/dataserver/CalendarFactory'
EDS_CALENDAR_FACTORY_INTERFACE = 'org.gnome.evolution.dataserver.CalendarFactory'

EDS_SOURCES_BUS_NAME = 'org.gnome.evolution.dataserver.Sources5'
EDS_SOURCE_MANAGER_PATH = '/org/gnome/evolution/dataserver/SourceManager'
EDS_SOURCE_MANAGER_INTERFACE = 'org.gnome.evolution.dataserver.SourceManager'
EDS_SOURCE_INTERFACE = 'org.gnome.evolution.dataserver.Source'

def get_dbus_proxy(bus_name, object_path, interface_name):
    """
    Helper to get a synchronus DBus proxy.
    """
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    return Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        bus_name,
        object_path,
        interface_name,
        None,
    )

def get_calendar_factory_proxy():
    return get_dbus_proxy(
        EDS_CALENDAR_BUS_NAME,
        EDS_CALENDAR_FACTORY_PATH,
        EDS_CALENDAR_FACTORY_INTERFACE
    )

def get_source_manager_proxy():
    return get_dbus_proxy(
        EDS_SOURCES_BUS_NAME,
        EDS_SOURCE_MANAGER_PATH,
        EDS_SOURCE_MANAGER_INTERFACE
    )

def get_calendar_proxy(calendar_uid):
    """
    Opens a calendar by UID using the CalendarFactory and returns a proxy to it.
    """
    factory = get_calendar_factory_proxy()
    
    # OpenCalendar returns (object_path, bus_name)
    # The signature is (s) -> (ss)
    result = factory.OpenCalendar('(s)', calendar_uid)
    object_path, bus_name = result
    
    return get_dbus_proxy(
        bus_name,
        object_path,
        'org.gnome.evolution.dataserver.Calendar' # The interface for calendar operations
    )

def find_calendar_uid_by_name(display_name):
    """
    Searches for a calendar source by its display name and returns its UID.
    """
    # We need to access the ObjectManager interface for SourceManager to list all objects
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    obj_manager = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        EDS_SOURCES_BUS_NAME,
        EDS_SOURCE_MANAGER_PATH,
        'org.freedesktop.DBus.ObjectManager',
        None,
    )
    
    objects = obj_manager.GetManagedObjects()
    for path, interfaces in objects.items():
        source = interfaces.get(EDS_SOURCE_INTERFACE)
        if source:
            data = source.get('Data', '')
            # Simple parsing of the keyfile-like data
            # Looking for DisplayName=... and [Calendar]
            if '[Calendar]' in data:
                # Check display name
                # This is a bit rough, a proper KeyFile parser would be better but this might accept raw string check
                if f'DisplayName={display_name}' in data:
                     return source.get('UID')
    return None
