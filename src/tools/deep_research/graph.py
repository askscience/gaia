"""
Orchestration logic for the Deep Research Agent using a parallel subagent approach.
"""

import asyncio
import time
from typing import Dict, Any, List
from src.tools.deep_research.state import AgentState

class DeepResearchGraph:
    """
    Parallel orchestration for the Deep Research Agent.
    """
    def __init__(self):
        self.cancelled = False
    
    def cancel(self):
        """Cancels the graph execution."""
        self.cancelled = True

    async def run(self, query: str, status_callback=None) -> AgentState:
        """
        Runs the graph for a given query in parallel.
        """
        from src.tools.deep_research.nodes import global_planner, section_researcher_node, synthesizer_node, image_researcher_node
        
        # Initial state
        state: AgentState = {
            "query": query,
            "outline": [],
            "notes": [],
            "report_sections": [],
            "images": [],
            "visited_urls": [],
            "report": None,
            "graph": self
        }
        
        self.cancelled = False
        
        # 1. Planning Phase
        if status_callback:
            status_callback("Planning research strategy (preparing sections)...", 5)
            
        plan_update = await global_planner(state)
        state.update(plan_update)
        
        if self.cancelled:
            state["report"] = "Research cancelled by user."
            return state

        outline = state.get("outline", [])
        section_plans = state.get("section_plans", {})
        
        if not outline:
            state["report"] = "Error: Failed to generate research outline."
            return state

        # 2. Image Research Phase (Early to provide a pool for sections)
        if status_callback:
            status_callback("Searching for high-quality images to include...", 15)
            
        image_update = await image_researcher_node(state)
        state["images"] = image_update.get("images", [])
        image_pool = state["images"]

        # 3. Parallel Research & Writing Phase
        if status_callback:
            status_callback(f"Starting {len(outline)} research subagents...", 20)

        # Track completed sections for progress bar
        completed_sections = 0
        total_sections = len(outline)
        
        # Calculate images per section (distribute pool uniquely)
        images_per_section = max(1, len(image_pool) // total_sections) if total_sections > 0 else 0

        async def run_subagent(section_index, section_title):
            nonlocal completed_sections
            sub_queries = section_plans.get(section_title, [])
            
            # Get a unique slice of images for this section
            start_idx = section_index * images_per_section
            end_idx = start_idx + images_per_section
            section_image_pool = image_pool[start_idx:end_idx] if image_pool else []
            
            # Sub-status update is tricky in parallel, so we use a shared counter
            result = await section_researcher_node(query, section_title, sub_queries, self, image_pool=section_image_pool)
            
            completed_sections += 1
            if status_callback:
                progress = 20 + int((completed_sections / total_sections) * 70)
                status_callback(f"Completed {completed_sections}/{total_sections}: {section_title}", progress)
            
            return result

        # Execute all sections in parallel
        subagent_tasks = [run_subagent(i, section) for i, section in enumerate(outline)]
        
        # Wait for all research subagents
        results = await asyncio.gather(*subagent_tasks)
        
        if self.cancelled:
            state["report"] = "Research cancelled by user."
            return state

        # 4. Aggregate Results
        all_notes = []
        all_sections = []
        
        # Map results back to outline order to maintain report structure
        results_map = {res["section"]: res for res in results if res and "section" in res}
        for section in outline:
            res = results_map.get(section)
            if res:
                all_notes.extend(res.get("notes", []))
                all_sections.append(res.get("content", ""))

        state["notes"] = all_notes
        state["report_sections"] = all_sections

        # 5. Final Synthesis
        if status_callback:
            status_callback("Synthesizing final comprehensive report...", 95)
            
        final_update = await synthesizer_node(state)
        state.update(final_update)
        
        if status_callback:
            status_callback("Report ready!", 100)
            
        return state
