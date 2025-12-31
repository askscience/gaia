"""
Orchestration logic for the Deep Research Agent using a State Graph approach.
"""

from typing import Dict, Any, Literal
from src.tools.deep_research.state import AgentState
from src.tools.deep_research.nodes import planner_node, researcher_node, writer_node, reflector_node, synthesizer_node

class DeepResearchGraph:
    """
    A simple async state machine implementation for the Deep Research Agent.
    """
    def __init__(self):
        self.nodes = {
            "plan": planner_node,
            "research": researcher_node,
            "writer": writer_node,
            "reflect": reflector_node,
            "synthesize": synthesizer_node
        }
        self.cancelled = False
    
    def cancel(self):
        """Cancels the graph execution."""
        self.cancelled = True

    def _get_next_node(self, state: AgentState) -> str:
        """
        Conditional logic to determine the next node after reflection.
        """
        if state.get("needs_more_info"):
            return "plan"  # Loop back to planning for more sub-queries
        return "synthesize"

    async def run(self, query: str, status_callback=None) -> AgentState:
        """
        Runs the graph for a given query.
        """
        # Initial state
        state: AgentState = {
            "query": query,
            "outline": [],
            "current_section_index": 0,
            "sub_queries": [],
            "notes": [],
            "report_sections": [],
            "visited_urls": [],
            "loop_count": 0,
            "report": None,
            "needs_more_info": False,
            "next_steps_reasoning": "Starting research process.",
            "graph": self
        }
        
        # Start with planning
        current_node_name = "plan"
        self.cancelled = False # Reset on new run
        
        while current_node_name:
            if self.cancelled:
                print("--- Research Cancelled ---")
                state["report"] = "Research cancelled by user."
                return state

            print(f"Executing Node: {current_node_name}")
            
            # Dynamic display name for UI spinner
            outline = state.get("outline", [])
            curr_idx = state.get("current_section_index", 0)
            section_title = outline[curr_idx] if outline and curr_idx < len(outline) else ""
            
            # Calculate completion percentage
            percentage = 0
            if outline:
                # Progress within sections (0 to 90%)
                base_progress = (curr_idx / len(outline)) * 90
                # Give some intermediate progress for nodes within a section
                node_bonus = 0
                if current_node_name == "research": node_bonus = 2
                elif current_node_name == "writer": node_bonus = 5
                elif current_node_name == "reflect": node_bonus = 8
                
                percentage = min(95, int(base_progress + node_bonus))
            elif current_node_name != "plan":
                percentage = 5
            
            if current_node_name == "synthesize":
                percentage = 98

            node_display_names = {
                "plan": f"Planning research for section: {section_title}" if section_title else "Planning research strategy...",
                "research": f"Searching and analyzing sources for: {section_title}" if section_title else "Searching and analyzing sources...",
                "writer": f"Drafting section: {section_title}" if section_title else "Drafting report sections...",
                "reflect": f"Evaluating findings for: {section_title}" if section_title else "Evaluating findings...",
                "synthesize": "Synthesizing final comprehensive report..."
            }
            
            display_name = node_display_names.get(current_node_name, f"Executing {current_node_name}...")
            
            if status_callback:
                try:
                    # Try calling with percentage, fallback to old signature if needed
                    status_callback(display_name, percentage=percentage)
                except TypeError:
                    status_callback(display_name)
                
            node_fn = self.nodes[current_node_name]
            
            # Execute node and update state
            update = await node_fn(state)
            
            # Merge updates into state (handling Annotated fields manually for this simple implementation)
            for k, v in update.items():
                if k in ["notes", "visited_urls", "report_sections"] and k in state:
                    state[k] += v # Append to existing lists
                else:
                    state[k] = v
            
            # Determine next step
            if current_node_name == "plan":
                current_node_name = "research"
            elif current_node_name == "research":
                current_node_name = "writer" # Incremental writing after research
            elif current_node_name == "writer":
                current_node_name = "reflect"
            elif current_node_name == "reflect":
                current_node_name = self._get_next_node(state)
            elif current_node_name == "synthesize":
                current_node_name = None # Finish
                
        return state
