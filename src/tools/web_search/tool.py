import json
from src.tools.base import BaseTool
from src.tools.web_search.search import search
from src.tools.web_search.scraper import scrape_url


class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web and retrieve clean content. "
            "Returns results in a structured format: [AI_CONTEXT] for your information, "
            "and [SOURCES] for the UI to display as cards. Do NOT repeat the URLs in your response."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default: 3)"
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str, max_results: int = 3, **kwargs):
        try:
            # 1. Search
            results = search(query, max_results=max_results)
            if not results or results[0].get("title") == "Error":
                return "No search results found or error occurred."

            # 2. Scrape & Build context
            sources = []
            ai_context = f"Search results for: {query}\n\n"
            
            for res in results:
                url = res.get("url")
                if not url:
                    continue
                
                scrape_res = scrape_url(url)
                content = scrape_res.get("content")
                
                # Add to sources for UI
                sources.append({
                    "title": res.get("title", "Untitled"),
                    "url": url,
                    "snippet": res.get("snippet", ""),
                    "image_url": scrape_res.get("image_url"),
                    "favicon_url": scrape_res.get("favicon_url")
                })
                
                # Add to context for AI
                ai_context += f"SOURCE: {res.get('title')}\n"
                if content:
                    ai_context += f"CONTENT: {content}\n"
                else:
                    ai_context += f"CONTENT: (Could not scrape full content) {res.get('snippet')}\n"
                ai_context += "---\n"

            # 3. Format structured response
            response = f"[AI_CONTEXT]\n{ai_context}\n[/AI_CONTEXT]\n\n"
            response += f"[SOURCES]\n{json.dumps(sources)}\n[/SOURCES]"
            
            return response

        except Exception as e:
            return f"Error: {str(e)}"
