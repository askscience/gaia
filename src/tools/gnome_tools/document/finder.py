import os
import subprocess
import fnmatch
from gi.repository import GLib

def find_files(filename: str, search_path: str = None, max_results: int = 5) -> list[str]:
    """
    Search for files by name in the user's home directory.
    Priority:
    1. Tracker3 (Instant, indexed search)
    2. XDG Directory Scan (Manual fallback)
    """
    results = []

    # 1. Try Tracker3 first (Fastest)
    try:
        # Construct SPARQL query for glob-like match
        # If filename contains '*', use 'glob' logic in SPARQL if possible, or simple contains
        # Simplest is just to match fileName
        
        # Note: Tracker SPARQL regex is heavy. We'll use naive contains for simple substring
        # or just fallback to manual scan if it's a complex glob.
        # But let's try a simple "contains" query first for speed.
        if '*' not in filename:
            # Simple substring match
            sparql = f"SELECT ?url {{ ?u a nfo:FileDataObject ; nfo:fileName ?name ; nie:url ?url . FILTER(CONTAINS(LCASE(?name), '{filename.lower()}')) }} LIMIT {max_results}"
            cmd = ["tracker3", "sparql", "--dbus-service", "org.freedesktop.Tracker3.Miner.Files", "-q", sparql]
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if proc.returncode == 0:
                lines = proc.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('file://'):
                        # Decode URI
                        path = line.replace('file://', '')
                        # rudimentary unquote
                        path = GLib.filename_from_uri(line)[0]
                        if path and os.path.exists(path):
                           results.append(path)
                
                if results:
                    return results[:max_results]
    except Exception:
        # Tracker failed or missing, proceed to manual
        pass

    # 2. Manual Fallback (XDG Dirs)
    if not search_path:
        search_path = os.path.expanduser("~")
    
    priority_dirs = []
    xdg_enums = [
        GLib.UserDirectory.DIRECTORY_DOCUMENTS,
        GLib.UserDirectory.DIRECTORY_DOWNLOAD,
        GLib.UserDirectory.DIRECTORY_DESKTOP,
        GLib.UserDirectory.DIRECTORY_MUSIC,
        GLib.UserDirectory.DIRECTORY_PICTURES,
        GLib.UserDirectory.DIRECTORY_VIDEOS
    ]
    
    for xdg_enum in xdg_enums:
        path = GLib.get_user_special_dir(xdg_enum)
        if path and os.path.exists(path):
            priority_dirs.append(path)
    
    # Add explicit search_path if provided and not in priority
    if search_path and search_path not in priority_dirs:
         priority_dirs.insert(0, search_path)

    for full_path in priority_dirs:
        if os.path.exists(full_path):
            for root, dirs, files in os.walk(full_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Check for exact match or glob match
                for f in files:
                    # 1. Exact match (case insensitive)
                    if f.lower() == filename.lower():
                        results.append(os.path.join(root, f))
                    # 2. Glob match
                    elif fnmatch.fnmatch(f.lower(), filename.lower()):
                         results.append(os.path.join(root, f))
                    # 3. Substring match (if no wildcard provided)
                    elif '*' not in filename and filename.lower() in f.lower():
                         results.append(os.path.join(root, f))

                    if len(results) >= max_results:
                        return results
                        
    return results[:max_results]
