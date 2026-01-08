
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.tools.web_search.search import search
from src.core.config import ConfigManager

def test_search_fallback():
    print("Testing search fallback logic...")
    
    # Ensure no API key is set
    config = ConfigManager()
    config.set("brave_search_api_key", "")
    
    print("Running search (should use DDG)...")
    results = search("test query", max_results=1)
    
    if results and "title" in results[0]:
        print("Search successful!")
        print(f"Result: {results[0]['title']}")
    else:
        print("Search returned no results or failed.")
        print(results)

if __name__ == "__main__":
    test_search_fallback()
