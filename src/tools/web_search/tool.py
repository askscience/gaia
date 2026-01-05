import json
from src.tools.base import BaseTool
from src.tools.web_search.search import search
from src.tools.web_search.scraper import scrape_url
from src.core.prompt_manager import PromptManager


class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web and retrieve clean content. "
            "Returns results in a structured format: [AI_CONTEXT] for your information, "
            "and [SOURCES] for the UI to display as cards. "
            "USE THIS TOOL ONLY ONCE per request with max_results=3. "
            "After calling this, you MUST use the scraped content to provide a detailed discursive answer."
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

    def execute(self, query: str, max_results: int = 3, status_callback=None, **kwargs):
        try:
            prompt_manager = PromptManager()
            if status_callback:
                status_callback(prompt_manager.get("web_search.status_searching", query=query))

            # 1. Search
            results = search(query, max_results=max_results)
            if not results:
                return prompt_manager.get("web_search.error_no_results")
            if results[0].get("title") == "Error":
                return prompt_manager.get("web_search.error_search", error=results[0].get('snippet'))

            # 2. Scrape & Build context
            sources = []
            ai_context = prompt_manager.get("web_search.context_header", query=query)
            
            for res in results:
                url = res.get("url")
                if not url:
                    continue
                
                scrape_res = scrape_url(url)
                content = scrape_res.get("content")
                
                # Add to sources for UI (prefer OpenGraph data when available)
                sources.append({
                    "title": scrape_res.get("og_title") or res.get("title", "Untitled"),
                    "url": url,
                    "snippet": scrape_res.get("og_description") or res.get("snippet", ""),
                    "image_url": scrape_res.get("image_url"),
                    "favicon_url": scrape_res.get("favicon_url")
                })
                
                # Add to context for AI
                ai_context += prompt_manager.get("web_search.context_source", title=res.get('title'))
                if content:
                    ai_context += prompt_manager.get("web_search.context_content", content=content)
                else:
                    ai_context += prompt_manager.get("web_search.context_content_partial", snippet=res.get('snippet'))
                ai_context += prompt_manager.get("web_search.context_separator")

            # 3. Format structured response
            return prompt_manager.get("web_search.response_format", context=ai_context, sources_json=json.dumps(sources))

        except Exception as e:
            return prompt_manager.get("web_search.error_generic", error=str(e))
