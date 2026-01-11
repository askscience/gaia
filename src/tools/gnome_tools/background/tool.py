import asyncio
import os
import requests
import json
import subprocess
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager
from src.core.config import ConfigManager

class GnomeSearchBackgroundTool(BaseTool):
    @property
    def name(self):
        return "gnome_search_background"

    @property
    def description(self):
        return "Searches for high-quality wallpapers using Unsplash or Pexels."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for wallpapers (e.g., 'nature', 'city')."
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str = "mountains", status_callback=None, **kwargs):
        pm = PromptManager()
        if status_callback:
            status_callback(pm.get("gnome_search_background.status_searching", query=query))
            
        async def fetch_images():
            from src.tools.deep_research.tools import async_search_unsplash, async_search_pexels
            config = ConfigManager()
            
            unsplash_key = config.get("unsplash_access_key", "")
            pexels_key = config.get("pexels_api_key", "")
            
            tasks = []
            if unsplash_key:
                tasks.append(async_search_unsplash(query, unsplash_key, max_results=4))
            if pexels_key:
                tasks.append(async_search_pexels(query, pexels_key, max_results=4))
                
            if not tasks:
                return []
                
            results = await asyncio.gather(*tasks)
            all_imgs = []
            for r in results:
                all_imgs.extend(r)
            return all_imgs[:4] # Return top 4 mixed

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            images = loop.run_until_complete(fetch_images())
            loop.close()
            
            if not images:
                print(f"[GnomeSearchBackground] No images found. Unsplash Key: {'Set' if unsplash_key else 'Missing'}, Pexels Key: {'Set' if pexels_key else 'Missing'}")
                return pm.get("gnome_search_background.error_no_keys")

            result_str = pm.get("gnome_search_background.success_header") + "\n\n"
            
            # Use raw JSON grid for UI rendering
            grid_data = []
            for img in images:
                grid_data.append({
                   "description": img.get('description', 'Image'),
                   "url": img['url'],
                   "attribution_name": img['attribution_name'],
                   "attribution_url": img['attribution_url'],
                   "source": img['source']
                })
            
            result_str += f"[WALLPAPER_GRID]{json.dumps(grid_data)}[/WALLPAPER_GRID]"
            result_str += f"\n\nFound {len(images)} wallpapers. [SYSTEM SEQUENCE: The wallpaper grid has been rendered to the user already. Do not repeat the data. Just say 'I found these wallpapers for you:' and list their titles briefly.]"
            
            return result_str
        except Exception as e:
            return pm.get("gnome_search_background.error_failed", error=str(e))


class GnomeSetBackgroundTool(BaseTool):
    @property
    def name(self):
        return "gnome_set_background"

    @property
    def description(self):
        return "Sets the desktop wallpaper from a URL."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the image to set as wallpaper."
                }
            },
            "required": ["url"]
        }

    def execute(self, url: str, status_callback=None, **kwargs):
        pm = PromptManager()
        if status_callback:
            status_callback(pm.get("gnome_set_background.status_setting"))
            
        try:
            # 1. Download image
            status_callback(pm.get("gnome_set_background.status_downloading")) if status_callback else None
            
            # Use a session with headers to mimic a browser, avoiding some 403/404s
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
            
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                 print(f"[GnomeSetBackground] Failed to download {url}. Status: {response.status_code}")
                 return pm.get("gnome_set_background.error_download", code=response.status_code)
                 
            # Save to local cache
            filename = url.split('/')[-1].split('?')[0] or "wallpaper.jpg"
            if not filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                filename += ".jpg"
                
            cache_dir = os.path.expanduser("~/.cache/gaia/wallpapers")
            os.makedirs(cache_dir, exist_ok=True)
            local_path = os.path.join(cache_dir, filename)
            
            with open(local_path, "wb") as f:
                f.write(response.content)
                
            # 2. Set with gsettings
            status_callback(pm.get("gnome_set_background.status_applying")) if status_callback else None
            uri = f"file://{local_path}"
            
            # Set for light and dark modes to be sure
            cmd = ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri]
            subprocess.run(cmd, check=True)
            
            cmd_dark = ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri]
            subprocess.run(cmd_dark, check=True)
            
            return pm.get("gnome_set_background.success")
            
        except Exception as e:
            return pm.get("gnome_set_background.error_failed", error=str(e))
