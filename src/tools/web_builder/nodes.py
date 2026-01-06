
import asyncio
import json
import os
from typing import List, Dict, Any
from src.tools.web_builder.state import AgentState, FilePlan
from src.core.ai_client import AIClient
from src.core.prompt_manager import PromptManager
from src.core.config import get_artifacts_dir

ai_client = AIClient()
prompt_manager = PromptManager()

async def async_generate_response(messages):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ai_client.generate_response, messages)

async def builder_planner(state: AgentState) -> Dict[str, Any]:
    """
    Generates a list of files to create based on the user description.
    """
    description = state["description"]
    project_id = state["project_id"]
    
    if state["graph"].cancelled: return {}
    
    print(f"--- Web Builder Planning: {description} ---")
    
    # Check if files are already provided? 
    # For now, we assume we always generate a plan from description if files_plan is empty.
    
    from src.core.config import ConfigManager
    config = ConfigManager()
    max_files = config.get("web_builder_max_files", 5)
    
    plan_prompt = prompt_manager.get("web_builder.plan_prompt", description=description, max_files=max_files)
    
    response = await async_generate_response([{"role": "user", "content": plan_prompt}])
    content = response["message"]["content"]
    
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        files_plan = json.loads(content)
    except:
        # Fallback or error
        return {"error": "Failed to generate file plan."}
        
    return {"files_plan": files_plan}

async def file_writer_node(filename: str, instruction: str, dependencies: List[str], state: AgentState) -> Dict[str, Any]:
    """
    Writes a single file.
    """
    if state["graph"].cancelled: return {}
    
    description = state["description"]
    project_id = state["project_id"]
    
    print(f"--- Writing File: {filename} ---")
    
    # Get full project structure to ensure imports are correct
    all_files = [f.get("filename") for f in state.get("files_plan", [])]
    project_structure = "\n".join(f"- {f}" for f in all_files)
    
    writer_prompt = prompt_manager.get(
        "web_builder.writer_prompt", 
        filename=filename, 
        instruction=instruction, 
        description=description,
        dependencies=", ".join(dependencies),
        project_structure=project_structure
    )
    
    response = await async_generate_response([{"role": "user", "content": writer_prompt}])
    content = response["message"]["content"]
    
    # Strip markdown code blocks if present
    if "```" in content:
        # Find first code block
        import re
        match = re.search(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            # Maybe it's just ``` ... ``` without language?
             content = content.replace("```", "")
    
    # Determine language
    _, ext = os.path.splitext(filename)
    ext = ext.lower().replace(".", "")
    if ext == "html": language = "html"
    elif ext == "css": language = "css"
    elif ext in ["js", "javascript"]: language = "javascript"
    else: language = "text"

    # Write file
    project_dir = os.path.join(get_artifacts_dir(), project_id)
    file_path = os.path.join(project_dir, filename)
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
            
        artifact_data = {
            "filename": filename,
            "path": file_path,
            "language": language,
            "type": "code" if language != "html" else "web"
        }
        
        return {
            "success": True, 
            "filename": filename, 
            "artifact": artifact_data,
            "message": prompt_manager.get("web_builder.success_file", filename=filename)
        }
    except Exception as e:
        return {
            "success": False, 
            "filename": filename, 
            "error": str(e),
             "message": prompt_manager.get("web_builder.error_file", filename=filename, error=str(e))
        }
