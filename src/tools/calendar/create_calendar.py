from .base import get_source_manager_proxy
import uuid

def create_calendar(display_name, color="#2ec27e"):
    """
    Creates a new local calendar.
    """
    source_manager = get_source_manager_proxy()
    
    # Generate a new UID
    new_uid = str(uuid.uuid4())
    
    # Construct KeyFile content
    # We create a local calendar.
    # Note: 'local-stub' is usually the parent for local calendars.
    # But often we can just specify the backend.
    
    # According to some sources, creating a source involves sending the keyfile content.
    keyfile_content = f"""
[Data Source]
DisplayName={display_name}
Enabled=true
Parent=local-stub

[Calendar]
BackendName=local
Color={color}
selected=true
"""
    
    try:
        # CreateSources takes a dictionary {uid: keyfile_content}
        # properly typed as a{ss}
        sources = {new_uid: keyfile_content}
        
        # calling CreateSources
        # We pass the signature as the first argument
        source_manager.CreateSources('(a{ss})', sources)
        print(f"Successfully created calendar '{display_name}' with UID {new_uid}")
        return new_uid
    except Exception as e:
        print(f"Error creating calendar: {e}")
        return None
