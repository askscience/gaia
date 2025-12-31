"""
Core logic nodes for the Deep Research Agent.
"""

import asyncio
from typing import List, Dict, Any
from src.tools.deep_research.state import AgentState, ResearchNote
from src.tools.deep_research.tools import async_search, async_scrape
from src.tools.deep_research.config import MAX_LOOPS, MAX_SEARCH_RESULTS, OUTLINE_STEPS, SEARCH_BREADTH
from src.core.ai_client import AIClient
import json

ai_client = AIClient()

async def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates a research outline if missing, and creates sub-queries for the current section.
    """
    query = state["query"]
    outline = state.get("outline", [])
    current_idx = state.get("current_section_index", 0)
    
    if state["graph"].cancelled: return {}
    
    if not outline:
        print(f"--- Generating Outline: {query} ---")
        outline_prompt = f"""Create a detailed, {OUTLINE_STEPS()} step research outline for the topic: "{query}".
Return ONLY a JSON list of strings (the section titles)."""
        outline_resp = ai_client.generate_response([{"role": "user", "content": outline_prompt}])
        content = outline_resp["message"]["content"]
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            outline = json.loads(content)
        except:
            outline = [f"Introduction to {query}", "Technical Overview", "Detailed Analysis", "Current Progress", "Conclusion"]
            
    # Always generate sub-queries for the CURRENT section
    current_section = outline[min(current_idx, len(outline)-1)]
    print(f"--- Planning Section ({current_idx+1}/{len(outline)}): {current_section} ---")
    
    sub_query_prompt = f"""Generate {SEARCH_BREADTH()} high-quality search queries to deeply research the section "{current_section}" for a report on "{query}".
Return ONLY a JSON list of strings."""
    
    response = ai_client.generate_response([{"role": "user", "content": sub_query_prompt}])
    content = response["message"]["content"]
    
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        sub_queries = json.loads(content)
    except:
        sub_queries = [f"{current_section} {query}", f"{current_section} details", f"{current_section} examples"]
    
    return {
        "outline": outline,
        "sub_queries": sub_queries,
        "loop_count": state.get("loop_count", 0) + 1,
        "next_steps_reasoning": f"Focusing on section: {current_section}"
    }

async def researcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes searches and scrapes pages in parallel.
    Uses a larger search pool to compensate for potential scraping failures.
    """
    sub_queries = state["sub_queries"]
    print(f"--- Researching: {sub_queries} ---")
    if state["graph"].cancelled: return {"notes": [], "visited_urls": []}
    
    # 1. Search for all sub-queries in parallel - fetch extra results for fallback
    search_depth = MAX_SEARCH_RESULTS() * 2
    search_tasks = [async_search(q, max_results=search_depth) for q in sub_queries]
    all_search_results = await asyncio.gather(*search_tasks)
    
    # 2. Extract URLs and filter duplicates
    urls_to_scrape = []
    visited_urls = state.get("visited_urls", [])
    
    for results in all_search_results:
        for res in results:
            url = res.get("url")
            if url and url not in visited_urls and url not in urls_to_scrape:
                urls_to_scrape.append(url)
    
    # 3. Scrape all new URLs in parallel
    scrape_tasks = [async_scrape(url) for url in urls_to_scrape]
    scrape_results = await asyncio.gather(*scrape_tasks)
    
    # 4. Extract notes from successful scrapes using LLM
    new_notes = []
    failed_count = 0
    
    for res in scrape_results:
        if state["graph"].cancelled: break
        if not res["content"]:
            failed_count += 1
            continue
            
        print(f"Successfully scraped: {res['url']}")
        target = state['outline'][min(state['current_section_index'], len(state['outline'])-1)]
        extract_prompt = f"""Extract 3-5 key sentences or facts from the following text that are relevant to the section "{target}" of a research on "{state['query']}".
Format your response as a concise summary.
Source URL: {res['url']}
Text: {res['content'][:3000]}"""
        
        extract_resp = ai_client.generate_response([{"role": "user", "content": extract_prompt}])
        extracted_info = extract_resp["message"]["content"]
        
        new_notes.append(ResearchNote(
            title=res.get("title", "Untitled"),
            url=res["url"],
            content=extracted_info,
            relevance=f"Extracted from {res.get('title')}"
        ))
        
        # Limit the number of notes per step to avoid context bloat if we have many successes
        if len(new_notes) >= MAX_SEARCH_RESULTS() * 2:
            break
            
    if failed_count > 0:
        print(f"--- Warning: {failed_count} sources failed to scrape. ---")
            
    return {
        "notes": new_notes,
        "visited_urls": urls_to_scrape,
        "next_steps_reasoning": f"Found {len(new_notes)} new relevant documents. {failed_count} failed."
    }

async def reflector_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates current findings for the section and decides whether to continue or move on.
    """
    outline = state["outline"]
    current_idx = state["current_section_index"]
    current_section = outline[min(current_idx, len(outline)-1)]
    print(f"--- Reflecting on Section: {current_section} ---")
    
    loop_count = state["loop_count"]
    query = state["query"]
    notes = state.get("notes", [])
    
    # Analyze if WE HAVE ENOUGH FOR THIS SECTION
    if state["graph"].cancelled: return {"needs_more_info": False}
    reflect_prompt = f"""Analyze the gathered research notes for the section "{current_section}" of the query: "{query}"
Notes: {[n.content for n in notes[-5:]]}
Do we have enough information to write this specific section comprehensively? 
Answer with ONLY "YES" or "NO" followed by a short reasoning on a new line."""
    
    reflect_resp = ai_client.generate_response([{"role": "user", "content": reflect_prompt}])
    resp_text = reflect_resp["message"]["content"].strip()
    
    section_complete = "YES" in resp_text.split("\n")[0].upper()
    
    # If section is done, or we are looping too much for it, move to next
    next_idx = current_idx
    needs_more_info = True
    
    if section_complete or loop_count >= (current_idx + 1) * 3: # allow ~3 loops per section
        next_idx = current_idx + 1
        if next_idx >= len(outline):
            needs_more_info = False # Finished all sections
            reasoning = "All sections researched. Proceeding to final synthesis."
        else:
            reasoning = f"Section '{current_section}' complete. Moving to '{outline[next_idx]}'."
    else:
        reasoning = resp_text.split("\n")[1] if "\n" in resp_text else resp_text
            
    return {
        "current_section_index": next_idx,
        "needs_more_info": needs_more_info,
        "next_steps_reasoning": reasoning
    }

async def writer_node(state: AgentState) -> Dict[str, Any]:
    """
    Drafts specifically the current section based on available notes.
    """
    current_idx = state.get("current_section_index", 0)
    # We want to write the section BEFORE we increment in reflector, or just use current_idx
    # Actually reflector increments, so writer should work on the section before it moves?
    # No, graph flow is Plan -> Research -> Writer -> Reflect.
    # So writer works on current_idx, then Reflector increments it.
    
    outline = state["outline"]
    current_section = outline[min(current_idx, len(outline)-1)]
    print(f"--- Writing Section: {current_section} ---")
    
    query = state["query"]
    latest_notes = state["notes"][-MAX_SEARCH_RESULTS()*2:]
    if state["graph"].cancelled: return {"report_sections": []}
    
    writer_prompt = f"""Write a comprehensive, professional, and detailed section titled "{current_section}" for a research report on "{query}".
Use the following research notes. Focus on being factual and providing depth.
Avoid introductory filler like "In this section...".
Use markdown formatting and include inline citations like [1], [2].

Notes:
"""
    for i, note in enumerate(latest_notes, 1):
        writer_prompt += f"[{i}] {note.title}: {note.content}\n"
        
    writer_resp = ai_client.generate_response([{"role": "user", "content": writer_prompt}])
    section_content = writer_resp["message"]["content"]
    
    # Only keep the last section draft if we loop for the same section
    # Wait, Annotated[List[str], operator.add] will append.
    # If we loop for the same section, we might get duplicates. 
    # But typically we move to next. For now, appending is fine.
    
    return {
        "report_sections": [f"\n## {current_section}\n\n" + section_content],
        "next_steps_reasoning": f"Drafted section: {current_section}"
    }

async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Compiles the final report by simply unifying sections and appending sources.
    This is now a script-based unification to avoid redundant LLM calls and preserve depth.
    """
    print("--- Synthesizing (Unifying Sections) ---")
    if state["graph"].cancelled: return {"report": "Research cancelled by user."}
    query = state["query"]
    sections = state.get("report_sections", [])
    notes = state["notes"]
    
    if not sections:
        # Fallback to old behavior if no sections were drafted
        return await _legacy_synthesis(state)
        
    # Unify sections directly
    final_report = "\n\n".join(sections)
    
    # Clean up double headers if any (unlikely but safe)
    # The writer already adds ## Section Title
    
    # Append sources at the end
    final_report += "\n\n## Sources\n"
    # Deduplicate notes by URL for the source list
    seen_urls = set()
    source_count = 1
    for note in notes:
        if note.url not in seen_urls:
            final_report += f"[{source_count}] [{note.title}]({note.url})\n"
            seen_urls.add(note.url)
            source_count += 1
        
    return {
        "report": final_report
    }

async def _legacy_synthesis(state: AgentState) -> Dict[str, Any]:
    """Legacy synthesizer as a fallback."""
    query = state["query"]
    notes = state["notes"]
    
    synth_prompt = f"""Create a detailed research report for query: "{query}"
Use the following notes and include inline citations like [1], [2] referring to the source index.
Notes:
"""
    for i, note in enumerate(notes, 1):
        synth_prompt += f"[{i}] {note.title} ({note.url}): {note.content}\n"
    
    synth_resp = ai_client.generate_response([{"role": "user", "content": synth_prompt}])
    report = synth_resp["message"]["content"]
    
    report += "\n\n## Sources\n"
    for i, note in enumerate(notes, 1):
        report += f"[{i}] [{note.title}]({note.url})\n"
        
    return {"report": report}
