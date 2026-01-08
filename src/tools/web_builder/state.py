from typing import TypedDict, List, Dict, Any, Optional

class FilePlan(TypedDict):
    filename: str
    instruction: str
    dependencies: List[str]

class AgentState(TypedDict):
    project_id: str
    description: str
    files_plan: List[FilePlan]
    completed_files: List[str]
    results: List[str]
    graph: Any # WebBuilderGraph
    error: Optional[str]
    file_contents: Dict[str, str]
