import os
from src.core.config import ConfigManager

def apply_proxy_settings():
    """
    Apply global proxy settings from configuration to environment variables.
    This affects requests, ddgs, and other libraries that respect HTTP_PROXY env vars.
    """
    config = ConfigManager()
    enabled = config.get("proxy_enabled", False)
    proxy_url = config.get("proxy_url", "").strip()

    if enabled and proxy_url:
        # Auto-fix missing scheme for Tor (common mistake)
        if (proxy_url.startswith("localhost:9050") or proxy_url.startswith("127.0.0.1:9050") or 
            proxy_url == "9050"):
            proxy_url = "socks5://" + proxy_url
        
        # Ensure scheme is present (default to http if missing and not matched above)
        if "://" not in proxy_url:
            proxy_url = "http://" + proxy_url

        # Remove verbose logging
        # print(f"[Network] Applying proxy settings: {proxy_url}")
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["ALL_PROXY"] = proxy_url
    else:
        # Clear if disabled or empty, but only if they were set by us (or general cleanup)
        # It's safer to just unset them to ensure clean state if user toggles off
        if "HTTP_PROXY" in os.environ:
            del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ:
            del os.environ["HTTPS_PROXY"]
        if "ALL_PROXY" in os.environ:
            del os.environ["ALL_PROXY"]
