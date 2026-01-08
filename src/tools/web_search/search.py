"""
DuckDuckGo search module.
Handles web search queries and returns structured results.
"""

import os
import sys
import certifi
from ddgs import DDGS
from typing import List, Dict, Optional
import traceback
import requests
from src.core.config import ConfigManager

# Force SSL cert file for frozen apps (curl_cffi/requests needs this)
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


def search_brave(query: str, api_key: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search using Brave Search API.
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    }
    params = {
        "q": query,
        "count": min(max_results, 20)  # Brave API max is 20
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", "") or item.get("extra_snippets", [""])[0]
            })
        
        # Limit to requested max_results
        return results[:max_results]
        
    except Exception as e:
        print(f"Brave Search failed: {e}")
        raise e  # Re-raise to trigger fallback


def search_ddg(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo (fallback).
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
         # Capture full traceback for debugging frozen app
        tb = traceback.format_exc()
        return [{"title": "Error", "url": "", "snippet": f"DDG Search failed: {str(e)} | Type: {type(e).__name__} | Traceback: {tb}"}]


def search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search for a query, prioritizing Brave Search if configured, else DuckDuckGo.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-10)
    
    Returns:
        List of results with 'title', 'url', and 'snippet' keys
    """
    config = ConfigManager()
    brave_key = config.get("brave_search_api_key")
    
    if brave_key:
        try:
            print(f"[DEBUG] Attempting Brave Search for: {query}")
            return search_brave(query, brave_key, max_results)
        except Exception as e:
            print(f"[DEBUG] Brave Search failed: {e}")
            # Fallback to DDG
            pass
            
    print(f"[DEBUG] Falling back to DuckDuckGo for: {query}")
    return search_ddg(query, max_results)


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
