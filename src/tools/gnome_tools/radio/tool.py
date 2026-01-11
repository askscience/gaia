import requests
import asyncio
import random
import json
import subprocess
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager

class GnomeRadioTool(BaseTool):
    @property
    def name(self):
        return "gnome_radio"

    @property
    def description(self):
        return "Search and listen to music, radio stations, or specific genres (e.g., 'jazz', 'lofi', 'rock')."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "play"],
                    "description": "The action to perform: 'search' for stations or 'play' a specific URL."
                },
                "query": {
                    "type": "string",
                    "description": "Search query (genre, name, country) for 'search' action."
                },
                "url": {
                    "type": "string",
                    "description": "The stream URL to play for 'play' action."
                }
            },
            "required": ["action"]
        }

    def execute(self, action: str, query: str = None, url: str = None, status_callback=None, **kwargs):
        pm = PromptManager()
        
        if action == "search":
             if not query:
                 return "Error: 'query' is required for search action."
             return self._search_stations(query, pm, status_callback)
        elif action == "play":
             if not url:
                 return "Error: 'url' is required for play action."
             return self._play_station(url, pm, status_callback)
        else:
             return f"Unknown action: {action}"

    def _get_api_server(self):
        # Try to get a working server from the main load balancer
        try:
            resp = requests.get("http://all.api.radio-browser.info/json/servers", timeout=5)
            servers = [s['name'] for s in resp.json()]
            if servers:
                return "https://" + random.choice(servers)
        except Exception:
            pass
            
        # Fallback to the one we know works
        return "https://de1.api.radio-browser.info"

    def _search_stations(self, query, pm, status_callback):
        if status_callback:
            status_callback(pm.get("gnome_radio.status_searching", query=query))
            
        try:
            base_url = self._get_api_server()
            # Search by name, tag, or country loosely
            api_url = f"{base_url}/json/stations/search"
            params = {
                'name': query,
                'limit': 8,
                'hidebroken': 'true',
                'order': 'clickcount',
                'reverse': 'true'
            }
            
            resp = requests.get(api_url, params=params, timeout=5)
            stations = resp.json()
            
            if not stations:
                # Try tag match if name fail
                params = {'tag': query, 'limit': 8, 'hidebroken': 'true', 'order': 'clickcount', 'reverse': 'true'}
                resp = requests.get(api_url, params=params, timeout=5)
                stations = resp.json()

            if not stations:
                return pm.get("gnome_radio.error_no_results", query=query)

            # Format for context
            results = []
            for st in stations:
                results.append({
                    "name": st['name'].strip(),
                    "url": st['url_resolved'],
                    "tags": st['tags'],
                    "country": st['country']
                })
            
            return pm.get("gnome_radio.success_search", count=len(results), json=json.dumps(results, indent=2))
            
        except Exception as e:
             return pm.get("gnome_radio.error_failed", error=str(e))

    def _play_station(self, url, pm, status_callback):
        if status_callback:
            status_callback(pm.get("gnome_radio.status_playing"))
            
        try:
            # Try specific media players first (in order of preference)
            # 1. Totem (Standard GNOME Videos)
            # 2. Rhythmbox (Standard GNOME Music)
            # 3. VLC (Commonly installed)
            # 4. MPV (Lightweight fallback)
            players = ["totem", "rhythmbox-client", "vlc", "mpv"]
            
            for player in players:
                # Check if player is available
                if subprocess.call(["which", player], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                    cmd = [player, url]
                    
                    # Rhythmbox needs --play-uri
                    if player == "rhythmbox-client":
                       cmd = ["rhythmbox-client", "--play-uri=" + url]
                       
                    # Launch detached
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return pm.get("gnome_radio.success_play", url=url)
            
            # Fallback to gio open (might open browser for http links)
            cmd = ["gio", "open", url]
            subprocess.run(cmd, check=True)
            return pm.get("gnome_radio.success_play", url=url)
        except Exception as e:
            return pm.get("gnome_radio.error_failed", error=str(e))
