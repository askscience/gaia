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
        from src.tools.deep_research.nodes import global_planner, section_researcher_node, synthesizer_node
        
        # Initial state
        state: AgentState = {
            "query": query,
            "outline": [],
            "notes": [],
            "report_sections": [],
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

        # 2. Parallel Research & Writing Phase
        if status_callback:
            status_callback(f"Starting {len(outline)} research subagents...", 10)

        # Track completed sections for progress bar
        completed_sections = 0
        total_sections = len(outline)

        async def run_subagent(section_title):
            nonlocal completed_sections
            sub_queries = section_plans.get(section_title, [])
            
            # Sub-status update is tricky in parallel, so we use a shared counter
            result = await section_researcher_node(query, section_title, sub_queries, self)
            
            completed_sections += 1
            if status_callback:
                progress = 10 + int((completed_sections / total_sections) * 80)
                status_callback(f"Completed {completed_sections}/{total_sections}: {section_title}", progress)
            
            return result

        # Execute all sections in parallel
        tasks = [run_subagent(section) for section in outline]
        
        results = await asyncio.gather(*tasks)
        
        if self.cancelled:
            state["report"] = "Research cancelled by user."
            return state

        # 3. Aggregate Results
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

        # 4. Final Synthesis
        if status_callback:
            status_callback("Synthesizing final comprehensive report...", 95)
            
        final_update = await synthesizer_node(state)
        state.update(final_update)
        
        if status_callback:
            status_callback("Report ready!", 100)
            
        return state
