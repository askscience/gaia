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
        Phase 2: Executes the file plan sequentially.
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
            status_callback(f"Starting sequential build of {total_files} files...", 20)
            
        state["status_callback"] = status_callback

        # SORT FILES: HTML first, then others (CSS, JS)
        # This ensures style classes and IDs exist before we implement logic/styling
        def sort_priority(f):
            fname = f.get("filename", "").lower()
            if fname.endswith(".html"): return 0
            if fname.endswith(".css"): return 1
            if fname.endswith(".js"): return 2
            return 3
            
        sorted_plan = sorted(files_plan, key=sort_priority)
        
        results = []
        messages = []
        artifacts = []
        
        for i, file_item in enumerate(sorted_plan):
            if self.cancelled:
                state["error"] = "Cancelled by user."
                break
                
            filename = file_item.get("filename")
            instruction = file_item.get("instruction")
            dependencies = file_item.get("dependencies", [])
            
            # Update status
            if status_callback:
                progress = 20 + int((completed_count / total_files) * 80)
                status_callback(f"Building {i+1}/{total_files}: {filename}...", progress)
            
            # Execute Node Sequentially
            # We don't need the concurrency manager here because we are running sequentially
            # However, the node 'file_writer_node' calls 'async_generate_response' which uses the semaphore.
            # So rate limiting is still active, but we only use 1 slot at a time here.
            try:
                res = await file_writer_node(filename, instruction, dependencies, state)
                results.append(res)
                
                if res.get("success"):
                    # IMMEDIATE CONTEXT UPDATE
                    # This is key: the next file will see this file's content
                    if res.get("content"):
                         state["file_contents"][filename] = res["content"]
                         print(f"--- [WebBuilder] Context updated with {filename} ---")
                    
                    artifacts.append(res["artifact"])
                    messages.append(res["message"])
                else:
                    messages.append(res.get("message", f"Failed: {filename}"))
                    
            except Exception as e:
                msg = f"Error building {filename}: {str(e)}"
                messages.append(msg)
                if status_callback: status_callback(msg)
            
            completed_count += 1
            
        state["results"] = messages
        state["artifacts"] = artifacts 
        
        return state
