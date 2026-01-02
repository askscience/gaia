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

ai_client = AIClient()

async def global_planner(state: AgentState) -> Dict[str, Any]:
    """
    Generates a full research outline and initial sub-queries for EVERY section upfront.
    """
    query = state["query"]
    if state["graph"].cancelled: return {}
    
    print(f"--- Global Planning: {query} ---")
    outline_prompt = f"""Create a detailed, {OUTLINE_STEPS()} step research outline for the topic: "{query}".
Return ONLY a JSON list of strings (the section titles)."""
    
    outline_resp = ai_client.generate_response([{"role": "user", "content": outline_prompt}])
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
        sub_query_prompt = f"""Generate {SEARCH_BREADTH()} high-quality search queries to deeply research the section "{section}" for a report on "{query}".
Return ONLY a JSON list of strings."""
        response = ai_client.generate_response([{"role": "user", "content": sub_query_prompt}])
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
    for res in scrape_results:
        if graph.cancelled: break
        if not res["content"]: continue
            
        extract_prompt = f"""Extract 3-5 key facts from the following text for the section "{section_title}" of research on "{query}".
Source: {res['url']}
Text: {res['content'][:3000]}"""
        
        extract_resp = ai_client.generate_response([{"role": "user", "content": extract_prompt}])
        extracted_info = extract_resp["message"]["content"]
        
        section_notes.append(ResearchNote(
            title=res.get("title", "Untitled"),
            url=res["url"],
            content=extracted_info,
            relevance=f"Source for {section_title}"
        ))

    # 2. Write Section
    if graph.cancelled: return {"notes": section_notes, "content": "", "section": section_title}
    
    if not section_notes:
        print(f"--- Warning: No notes found for section {section_title} ---")
        return {"notes": [], "content": f"\n## {section_title}\n\n*No specific research data was found for this section.*", "section": section_title}

    print(f"--- Subagent Writing Section: {section_title} ---")
    
    writer_prompt = f"""Write a comprehensive, professional section titled "{section_title}" for a research report on "{query}".
Use these notes and include inline citations like [1], [2].
Avoid introductory filler. Use markdown.

CRITICAL: Do NOT include the title "{section_title}" or any #/## headers with the section name at the beginning. The title is already handled by the system. Start directly with the content.

"""
    if image_pool:
        writer_prompt += "You have a pool of high-quality images available. If an image is highly relevant to a paragraph, insert it using standard markdown: ![description](url).\n"
        writer_prompt += "Only use images from this list. Do not use more than 1-2 images per section. Place them between paragraphs where they provide visual context.\n"
        writer_prompt += "Available Images:\n"
        for img in image_pool:
            writer_prompt += f"- ![{img['description']}]({img['url']})\n"
        writer_prompt += "\n"

    writer_prompt += "Notes:\n"
    for i, note in enumerate(section_notes, 1):
        writer_prompt += f"[{i}] {note.title}: {note.content}\n"
        
    writer_resp = ai_client.generate_response([{"role": "user", "content": writer_prompt}])
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
    img_query_prompt = f"""Generate 2 distinct, high-quality search keywords for a research report on "{query}".
Each keyword MUST BE short, between 1 and 3 words max.
Return ONLY a JSON list of strings."""
    
    response = ai_client.generate_response([{"role": "user", "content": img_query_prompt}])
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
    final_report += "\n\n"
    seen_urls = set()
    source_count = 1
    for note in notes:
        if note.url not in seen_urls:
            final_report += f"[{source_count}] [{note.title}]({note.url})\n"
            seen_urls.add(note.url)
            source_count += 1
        
    return {"report": final_report, "final_images": images}
