"""
Web content scraper module.
Extracts clean, readable content from web pages.
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional

# Common user agent for requests
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Elements to remove from pages
REMOVE_TAGS = [
    "script", "style", "nav", "header", "footer",
    "aside", "form", "iframe", "noscript", "meta",
    "link", "button", "input", "select", "textarea",
    "svg", "canvas", "video", "audio"
]

# CSS selectors for elements to remove (ads, navigation, etc.)
REMOVE_SELECTORS = [
    "[class*='nav']", "[class*='menu']", "[class*='sidebar']",
    "[class*='footer']", "[class*='header']", "[class*='ad-']",
    "[class*='advertisement']", "[class*='cookie']", "[class*='popup']",
    "[class*='modal']", "[class*='banner']", "[class*='social']",
    "[class*='share']", "[class*='comment']", "[class*='related']",
    "[id*='nav']", "[id*='menu']", "[id*='sidebar']",
    "[id*='footer']", "[id*='header']", "[id*='ad']",
    "[id*='cookie']", "[id*='popup']", "[id*='modal']"
]


# Selectors to try for finding main content
MAIN_CONTENT_SELECTORS = [
    "article", "main", "[role='main']", 
    ".article-body", ".article-content", ".post-content",
    ".entry-content", ".content", "#content", 
    ".post", ".article", ".story"
]


def scrape_url(url: str, max_length: int = 3000, timeout: int = 10) -> dict:
    """
    Scrape and extract clean text content and metadata from a URL.
    
    Args:
        url: URL to scrape
        max_length: Maximum content length to return
        timeout: Request timeout in seconds
    
    Returns:
        Dict with 'content', 'image_url', 'favicon_url', 'og_title', and 'og_description'
    """
    result = {
        "content": None, 
        "image_url": None, 
        "favicon_url": None,
        "og_title": None,
        "og_description": None
    }
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout
        )
        response.raise_for_status()
        
        # Try trafilatura first for high-quality extraction
        try:
            try:
            try:
                import trafilatura
                from trafilatura.settings import use_config
                from src.core.config import ConfigManager
                
                # Load settings from app config (JSON-based)
                app_config = ConfigManager()
                scrape_settings = app_config.get("scrape_settings", {})
                
                # Use default Trafilatura config as base to ensure all required keys exist
                traf_config = use_config()
                
                # Set defaults or user-provided values
                # Note: ConfigParser keys are case-insensitive
                traf_config.set("DEFAULT", "min_extracted_size", str(scrape_settings.get("min_extracted_size", 250)))
                traf_config.set("DEFAULT", "min_output_size", str(scrape_settings.get("min_output_size", 1)))
                traf_config.set("DEFAULT", "min_extracted_comm_size", str(scrape_settings.get("min_extracted_comm_size", 1)))
                traf_config.set("DEFAULT", "min_output_comm_size", str(scrape_settings.get("min_output_comm_size", 1)))
                traf_config.set("DEFAULT", "extraction_timeout", str(scrape_settings.get("extraction_timeout", 0)))

                # valid_result=True ensures we don't get empty strings if uncertain
                trafilatura_content = trafilatura.extract(
                    response.content, 
                    include_comments=False,
                    config=traf_config
                )
                if trafilatura_content:
                    if len(trafilatura_content) > max_length:
                        trafilatura_content = trafilatura_content[:max_length] + "..."
                    result["content"] = trafilatura_content
            except Exception as e:
                print(f"Trafilatura extraction failed: {e}")
        except ImportError:
            pass

        soup = BeautifulSoup(response.content, "lxml")
        
        # 1. Extract OpenGraph Title
        og_title = (soup.find("meta", property="og:title") or 
                   soup.find("meta", attrs={"name": "og:title"}))
        if og_title:
            result["og_title"] = og_title.get("content")
        
        # Fallback to standard title
        if not result["og_title"] and soup.title:
            result["og_title"] = soup.title.string

        # 2. Extract OpenGraph Description
        og_desc = (soup.find("meta", property="og:description") or 
                  soup.find("meta", attrs={"name": "description"}) or
                  soup.find("meta", attrs={"name": "og:description"}))
        if og_desc:
            result["og_description"] = og_desc.get("content")
        
        # 3. Extract OpenGraph or Featured Image
        og_image = (soup.find("meta", property="og:image") or 
                   soup.find("meta", attrs={"name": "og:image"}) or
                   soup.find("meta", itemprop="image"))
        if og_image:
            result["image_url"] = og_image.get("content")
        
        # 4. Extract Favicon (try multiple common patterns)
        icon_patterns = [
            {"rel": "apple-touch-icon"},
            {"rel": "apple-touch-icon-precomposed"},
            {"rel": "icon", "type": "image/png"},
            {"rel": "shortcut icon"},
            {"rel": "icon"}
        ]
        
        for pattern in icon_patterns:
            icon_link = soup.find("link", attrs=pattern)
            if icon_link:
                icon_url = icon_link.get("href")
                if icon_url:
                    if not icon_url.startswith('http'):
                        from urllib.parse import urljoin
                        icon_url = urljoin(url, icon_url)
                    result["favicon_url"] = icon_url
                    break

        # 5. Clean and extract content (only if trafilatura didn't work)
        if not result["content"]:
            _remove_unwanted_elements(soup)
            main_content = _find_main_content(soup)
            text = _extract_text(main_content)
            
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            result["content"] = text.strip() if text.strip() else None
            
        return result
        
    except Exception as e:
        return result


def _remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove unwanted tags and elements from the soup."""
    # Remove by tag name
    for tag in REMOVE_TAGS:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove by CSS selector
    for selector in REMOVE_SELECTORS:
        try:
            for element in soup.select(selector):
                element.decompose()
        except Exception:
            pass  # Some selectors may fail, that's ok


def _find_main_content(soup: BeautifulSoup):
    """Find the main content area of the page."""
    for selector in MAIN_CONTENT_SELECTORS:
        content = soup.select_one(selector)
        if content:
            return content
    
    # Fallback to body
    return soup.body if soup.body else soup


def _extract_text(element) -> str:
    """Extract clean text from a BeautifulSoup element."""
    if not element:
        return ""
    
    # Collect text from meaningful elements
    paragraphs = []
    
    for tag in element.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
        text = tag.get_text(separator=" ", strip=True)
        # Filter short fragments (likely navigation/buttons)
        if text and len(text) > 30:
            paragraphs.append(text)
    
    if paragraphs:
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for p in paragraphs:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return "\n\n".join(unique)
    
    # Fallback: get all text
    text = element.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 30]
    
    # Remove duplicates
    seen = set()
    unique = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    
    return "\n\n".join(unique)
