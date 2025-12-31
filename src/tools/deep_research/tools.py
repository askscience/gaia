"""
Async tools for web search and scraping, wrapping existing logic.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import trafilatura
from typing import List, Dict, Optional
from src.tools.web_search.search import search
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
    Async scraping using aiohttp and trafilatura.
    """
    result = {"content": None, "title": None, "url": url}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=SCRAPE_TIMEOUT) as response:
                if response.status == 200:
                    # Always read as bytes and decode with 'replace' for maximum robustness
                    content_bytes = await response.read()
                    html = content_bytes.decode(errors='replace')
                    
                    # Use trafilatura for high-quality markdown extraction
                    content = trafilatura.extract(html)
                    
                    if not content:
                        # Fallback to simple BeautifulSoup extraction
                        soup = BeautifulSoup(html, "lxml")
                        # Basic cleanup
                        for tag in ["script", "style", "nav", "footer", "header"]:
                            for el in soup.find_all(tag):
                                el.decompose()
                        content = soup.get_text(separator="\n", strip=True)
                    
                    if content and len(content) > MAX_SCRAPE_LENGTH():
                        content = content[:MAX_SCRAPE_LENGTH()] + "..."
                        
                    result["content"] = content
                    
                    # Extract title
                    soup = BeautifulSoup(html, "lxml")
                    result["title"] = soup.title.string if soup.title else "Untitled"
                    
        return result
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return result
