"""
Entry point for the Deep Research Agent.
"""

import asyncio
import sys
from src.tools.deep_research.graph import DeepResearchGraph

async def main():
    """
    Runs a sample research query.
    """
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "The impact of quantum computing on modern cryptography"
        
    print(f"Starting Deep Research for: {query}")
    
    agent = DeepResearchGraph()
    final_state = await agent.run(query)
    
    print("\n" + "="*50)
    print("FINAL RESEARCH REPORT")
    print("="*50)
    print(final_state["report"])
    
if __name__ == "__main__":
    asyncio.run(main())
