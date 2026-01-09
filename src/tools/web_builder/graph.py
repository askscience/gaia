import asyncio
from typing import Dict, Any, List
from src.tools.web_builder.state import AgentState
from src.tools.web_builder.nodes import builder_planner, file_writer_node

class WebBuilderGraph:
    def __init__(self):
        self.cancelled = False
        
    def cancel(self):
        self.cancelled = True
        
    async def plan(self, description: str, project_id: str, status_callback=None) -> AgentState:
        """
        Phase 1: Generates the file plan.
        """
        state: AgentState = {
            "project_id": project_id,
            "description": description,
            "files_plan": [],
            "completed_files": [],
            "results": [],
            "graph": self,
            "error": None
        }
        
        self.cancelled = False
        
        if status_callback:
            status_callback("Planning project structure...", 10)
            
        plan_update = await builder_planner(state)
        if "error" in plan_update:
            state["error"] = plan_update["error"]
            return state
            
        state.update(plan_update)
        files_plan = state.get("files_plan", [])
        
        if not files_plan:
             state["error"] = "No files in plan."
        
        return state

    async def execute_from_plan(self, state: AgentState, status_callback=None) -> AgentState:
        """
        Phase 2: Executes the file plan.
        """
        self.cancelled = False
        files_plan = state.get("files_plan", [])
        
        if not files_plan:
            state["error"] = "No plan to execute."
            return state
            
        # 2. Execution
        total_files = len(files_plan)
        completed_count = 0
        state["file_contents"] = {} # Initialize
        
        if status_callback:
            status_callback(f"Starting {total_files} subagents to write files...", 20)
            
        from src.core.concurrency.manager import ConcurrencyManager
        concurrency_manager = ConcurrencyManager()

        async def run_subagent(file_item):
            nonlocal completed_count
            filename = file_item["filename"]
            instruction = file_item["instruction"]
            dependencies = file_item.get("dependencies", [])
            
            async with concurrency_manager.get_async_semaphore():
                # Subagent specific execution
                result = await file_writer_node(filename, instruction, dependencies, state)
            
            completed_count += 1
            if status_callback:
                progress = 20 + int((completed_count / total_files) * 80)
                status_callback(f"Built {completed_count}/{total_files}: {filename}", progress)
                
            return result
        
        # Separate HTML files (to run LAST) from assets (CSS, JS, etc.)
        html_files = [f for f in files_plan if f.get("filename", "").endswith(".html")]
        asset_files = [f for f in files_plan if not f.get("filename", "").endswith(".html")]
        
        # Run assets in parallel first
        asset_tasks = [run_subagent(f) for f in asset_files]
        asset_results = await asyncio.gather(*asset_tasks)
        
        # Collect content from assets for the next phase
        for res in asset_results:
            if res.get("success") and res.get("content"):
                state["file_contents"][res["filename"]] = res["content"]
        
        if self.cancelled:
            state["error"] = "Cancelled by user."
            return state
        
        # Then run HTML files (index.html) last, so they know all assets exist
        html_tasks = [run_subagent(f) for f in html_files]
        html_results = await asyncio.gather(*html_tasks)
        
        results = list(asset_results) + list(html_results)
        
        if self.cancelled:
            state["error"] = "Cancelled by user."
            return state
            
        # Aggregate
        artifacts = []
        messages = []
        for res in results:
            if res.get("success"):
                artifacts.append(res["artifact"])
                messages.append(res["message"])
            else:
                messages.append(res.get("message", f"Failed: {res.get('filename')}"))
                
        state["results"] = messages
        state["artifacts"] = artifacts 
        
        return state
