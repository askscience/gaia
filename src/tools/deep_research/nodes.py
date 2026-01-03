"""
Core logic nodes for the Deep Research Agent.
"""

import asyncio
import json
from typing import List, Dict, Any
from src.tools.deep_research.state import AgentState, ResearchNote
from src.tools.deep_research.tools import async_search, async_scrape, async_search_unsplash, async_search_pexels
from src.tools.deep_research.config import MAX_LOOPS, MAX_SEARCH_RESULTS, OUTLINE_STEPS, SEARCH_BREADTH, UNSPLASH_KEY, PEXELS_KEY
from src.core.ai_client import AIClient
from src.core.prompt_manager import PromptManager

ai_client = AIClient()
prompt_manager = PromptManager()


async def async_generate_response(messages):
    """
    Async wrapper for AI client generation to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ai_client.generate_response, messages)

async def global_planner(state: AgentState) -> Dict[str, Any]:
    """
    Generates a full research outline and initial sub-queries for EVERY section upfront.
    """
    query = state["query"]
    if state["graph"].cancelled: return {}
    
    print(f"--- Global Planning: {query} ---")

    print(f"--- Global Planning: {query} ---")

    outline_prompt = prompt_manager.get(
        "deep_research.outline", 
        query=query, 
        outline_steps=OUTLINE_STEPS()
    )
    
    outline_resp = await async_generate_response([{"role": "user", "content": outline_prompt}])
    content = outline_resp["message"]["content"]
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        outline = json.loads(content)
    except:
        outline = [f"Introduction to {query}", "Key Concepts", "Detailed Technical Analysis", "Challenges and Opportunities", "Future Outlook", "Conclusion"]

    # Now generate sub-queries for EACH section in parallel
    section_plans = {}
    for section in outline:
        sub_query_prompt = prompt_manager.get(
            "deep_research.sub_queries",
            search_breadth=SEARCH_BREADTH(),
            section=section,
            query=query
        )
        response = await async_generate_response([{"role": "user", "content": sub_query_prompt}])
        content = response["message"]["content"]
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            sub_queries = json.loads(content)
        except:
            sub_queries = [f"{section} {query}", f"{section} details"]
        section_plans[section] = sub_queries

    return {
        "outline": outline,
        "section_plans": section_plans,
        "next_steps_reasoning": f"Generated outline with {len(outline)} sections. Ready for parallel research."
    }

async def section_researcher_node(query: str, section_title: str, sub_queries: List[str], graph: Any, image_pool: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    A standalone researcher + writer node for a specific section.
    Designed to be run as a subagent in parallel.
    """
    if graph.cancelled: return {"notes": [], "content": "", "section": section_title}
    print(f"--- Subagent Researching Section: {section_title} ---")
    
    # 1. Search & Scrape
    search_depth = MAX_SEARCH_RESULTS()
    search_tasks = [async_search(q, max_results=search_depth) for q in sub_queries]
    all_search_results = await asyncio.gather(*search_tasks)
    
    urls_to_scrape = []
    for results in all_search_results:
        for res in results:
            url = res.get("url")
            if url and url not in urls_to_scrape:
                urls_to_scrape.append(url)
    
    # Scrape top URLs to keep it fast but deep
    scrape_tasks = [async_scrape(url) for url in urls_to_scrape[:5]]
    scrape_results = await asyncio.gather(*scrape_tasks)
    
    section_notes = []
    
    # Process extractions concurrently to avoid serial blocking
    async def process_extraction(res):
        if not res["content"]: return None
        
        extract_prompt = prompt_manager.get(
            "deep_research.extract",
            section_title=section_title,
            query=query,
            url=res['url'],
            content=res['content'][:3000]
        )
        
        extract_resp = await async_generate_response([{"role": "user", "content": extract_prompt}])
        extracted_info = extract_resp["message"]["content"]
        
        return ResearchNote(
            title=res.get("title", "Untitled"),
            url=res["url"],
            content=extracted_info,
            relevance=f"Source for {section_title}"
        )

    # Launch extraction tasks in parallel
    extraction_tasks = [process_extraction(res) for res in scrape_results]
    extraction_results = await asyncio.gather(*extraction_tasks)
    
    for note in extraction_results:
        if graph.cancelled: break
        if note:
            section_notes.append(note)

    # 2. Write Section
    if graph.cancelled: return {"notes": section_notes, "content": "", "section": section_title}
    
    if not section_notes:
        print(f"--- Warning: No notes found for section {section_title} ---")
        return {"notes": [], "content": f"\n## {section_title}\n\n*No specific research data was found for this section.*", "section": section_title}

    print(f"--- Subagent Writing Section: {section_title} ---")
    
    writer_prompt = prompt_manager.get("deep_research.write_section", section_title=section_title, query=query)
    
    if image_pool:
        writer_prompt += prompt_manager.get("deep_research.write_section_images")
        for img in image_pool:
            writer_prompt += f"- ![{img['description']}]({img['url']})\n"
        writer_prompt += "\n"

    writer_prompt += "Notes:\n"
    for i, note in enumerate(section_notes, 1):
        writer_prompt += f"* {note.title}: {note.content}\n  URL: {note.url}\n"
        
    writer_resp = await async_generate_response([{"role": "user", "content": writer_prompt}])
    section_content = f"\n## {section_title}\n\n" + writer_resp["message"]["content"]
    
    return {
        "notes": section_notes,
        "content": section_content,
        "section": section_title
    }

async def image_researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Subagent that searches for relevant high-quality images.
    """
    query = state["query"]
    if state["graph"].cancelled: return {"images": []}
    
    unsplash_key = UNSPLASH_KEY()
    pexels_key = PEXELS_KEY()
    
    if not unsplash_key and not pexels_key:
        return {"images": []}
        
    # Generate image search queries
    img_query_prompt = prompt_manager.get("deep_research.image_query", query=query)
    
    response = await async_generate_response([{"role": "user", "content": img_query_prompt}])
    content = response["message"]["content"]
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        img_queries = json.loads(content)
    except:
        # Fallback to simple keywords
        img_queries = [query.split()[:2], "professional context"]
        img_queries = [" ".join(q) if isinstance(q, list) else q for q in img_queries]

    all_images = []
    
    # Run searches in parallel
    search_tasks = []
    for q in img_queries:
        if unsplash_key:
            search_tasks.append(async_search_unsplash(q, unsplash_key, max_results=3))
        if pexels_key:
            search_tasks.append(async_search_pexels(q, pexels_key, max_results=3))
            
    if not search_tasks:
        return {"images": []}
        
    search_results = await asyncio.gather(*search_tasks)
    
    for results in search_results:
        all_images.extend(results)
        
    # Deduplicate by URL
    unique_images = []
    seen_urls = set()
    for img in all_images:
        if img["url"] not in seen_urls:
            unique_images.append(img)
            seen_urls.add(img["url"])
            
    return {"images": unique_images[:10]}

async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Compiles the final report by simply unifying sections and appending sources.
    No AI call here to ensure speed and prevent truncation.
    """
    print("--- Synthesizing Report ---")
    if state.get("graph") and state["graph"].cancelled: 
        return {"report": "Research cancelled by user."}
        
    sections = state.get("report_sections", [])
    notes = state.get("notes", [])
    images = state.get("images", [])
    
    if not sections:
        return {"report": "## Error\nNo content was generated for this report. Please check your connectivity or try a different topic."}
        
    final_report = "\n\n".join(sections)
    
    # Append sources at the end
    # Note: Header "Sources" is added by the HTML template
    # final_report += "\n\n"
    # seen_urls = set()
    # source_count = 1
    # for note in notes:
    #     if note.url not in seen_urls:
    #         final_report += f"[{source_count}] [{note.title}]({note.url})\n"
    #         seen_urls.add(note.url)
    #         source_count += 1
        
    return {"report": final_report, "final_images": images}
