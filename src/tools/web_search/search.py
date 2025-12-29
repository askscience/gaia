"""
DuckDuckGo search module.
Handles web search queries and returns structured results.
"""

from ddgs import DDGS
from typing import List, Dict, Optional


def search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for a query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-10)
    
    Returns:
        List of results with 'title', 'url', and 'snippet' keys
    """
    max_results = max(1, min(max_results, 10))
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        
        results = []
        for r in raw_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
        
        return results
        
    except Exception as e:
        return [{"title": "Error", "url": "", "snippet": f"Search failed: {str(e)}"}]


def search_news(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo News for a query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-10)
    
    Returns:
        List of news results with 'title', 'url', 'snippet', and 'date' keys
    """
    max_results = max(1, min(max_results, 10))
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.news(query, max_results=max_results))
        
        results = []
        for r in raw_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("body", ""),
                "date": r.get("date", ""),
                "source": r.get("source", "")
            })
        
        return results
        
    except Exception as e:
        return [{"title": "Error", "url": "", "snippet": f"News search failed: {str(e)}"}]
