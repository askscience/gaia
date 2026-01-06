
import os
import httpx
from src.core.config import ConfigManager

def get_httpx_client(timeout=1200.0):
    """
    Creates an httpx.Client configured with the global proxy settings.
    Handles SOCKS proxies via httpx_socks if needed.
    """
    config = ConfigManager()
    proxy_url = config.get("proxy_url", "").strip()
    enabled = config.get("proxy_enabled", False)

    # If proxy disabled or empty, return None to let SDKs use defaults (or create standard client)
    if not enabled or not proxy_url:
        return httpx.Client(timeout=timeout)

    # Standardize scheme if missing
    if "://" not in proxy_url:
        if (proxy_url.startswith("localhost:9050") or proxy_url.startswith("127.0.0.1:9050") or 
            proxy_url == "9050"):
            proxy_url = "socks5://" + proxy_url
        else:
            proxy_url = "http://" + proxy_url 

    print(f"[Network] Configured Proxy: {proxy_url}")

    if proxy_url.startswith("socks"):
        try:
            from httpx_socks import SyncTransport
            transport = SyncTransport.from_url(proxy_url)
            return httpx.Client(transport=transport, timeout=timeout)
        except ImportError:
            print("Error: httpx-socks not installed. Cannot use SOCKS proxy.")
            return httpx.Client(timeout=timeout)
        except Exception as e:
            print(f"Error creating SOCKS transport: {e}")
            return httpx.Client(timeout=timeout)
    else:
        # Standard HTTP/HTTPS proxy
        return httpx.Client(proxy=proxy_url, timeout=timeout)

def get_async_httpx_client(timeout=1200.0):
    """
    Creates an httpx.AsyncClient with proxy support.
    """
    config = ConfigManager()
    proxy_url = config.get("proxy_url", "").strip()
    enabled = config.get("proxy_enabled", False)

    if not enabled or not proxy_url:
        return httpx.AsyncClient(timeout=timeout)

    if proxy_url.startswith("socks"):
        try:
            from httpx_socks import AsyncTransport
            transport = AsyncTransport.from_url(proxy_url)
            return httpx.AsyncClient(transport=transport, timeout=timeout)
        except ImportError:
            return httpx.AsyncClient(timeout=timeout)
    else:
        return httpx.AsyncClient(proxy=proxy_url, timeout=timeout)
