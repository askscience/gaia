"""
Async tools for web search and scraping, wrapping existing logic.
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from src.tools.web_search.search import search
from src.tools.web_search.scraper import scrape_url
from src.tools.deep_research.config import SEARCH_TIMEOUT, SCRAPE_TIMEOUT, MAX_SCRAPE_LENGTH

async def async_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Async wrapper for the DuckDuckGo search.
    Since ddgs is synchronous, we run it in a thread pool.
    """
    loop = asyncio.get_event_loop()
    # Using run_in_executor to avoid blocking the event loop
    return await loop.run_in_executor(None, search, query, max_results)

async def async_scrape(url: str) -> Dict[str, Optional[str]]:
    """
    Async scraping using the centralized web_search scraper.
    """
    loop = asyncio.get_event_loop()
    
    # Run sync scraper in executor
    try:
        scraped_data = await loop.run_in_executor(
            None, 
            scrape_url, 
            url, 
            MAX_SCRAPE_LENGTH(), 
            SCRAPE_TIMEOUT
        )
        
        # Map to expected format
        return {
            "content": scraped_data.get("content"),
            "title": scraped_data.get("og_title") or "Untitled",
            "url": url
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {"content": None, "title": None, "url": url}

async def async_search_unsplash(query: str, access_key: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for images on Unsplash.
    """
    images = []
    if not access_key:
        return images

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": max_results,
        "client_id": access_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("results", []):
                        user = item.get("user", {})
                        images.append({
                            "url": item.get("urls", {}).get("regular"),
                            "thumb": item.get("urls", {}).get("small"),
                            "description": item.get("description") or item.get("alt_description") or query,
                            "attribution_name": f"Unsplash/{user.get('username') or user.get('name')}",
                            "attribution_url": user.get("links", {}).get("html"),
                            "source": "Unsplash"
                        })
    except Exception as e:
        print(f"Unsplash API error: {e}")
    
    return images

async def async_search_pexels(query: str, api_key: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for images on Pexels.
    """
    images = []
    if not api_key:
        return images

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": max_results
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("photos", []):
                        images.append({
                            "url": item.get("src", {}).get("large"),
                            "thumb": item.get("src", {}).get("medium"),
                            "description": item.get("alt") or query,
                            "attribution_name": f"Pexels/{item.get('photographer')}",
                            "attribution_url": item.get("photographer_url"),
                            "source": "Pexels"
                        })
    except Exception as e:
        print(f"Pexels API error: {e}")
    
    return images
