from src.core.config import ConfigManager

config = ConfigManager()

# Maximum internal loops for refinement
def MAX_LOOPS():
    return config.get("dr_max_loops", 3)

def MAX_SEARCH_RESULTS():
    return config.get("dr_max_results", 3)

def MAX_SCRAPE_LENGTH():
    return config.get("dr_max_scrape_length", 5000)

def OUTLINE_STEPS():
    return config.get("dr_outline_steps", 5)

def SEARCH_BREADTH():
    return config.get("dr_search_breadth", 3)

# LLM Configuration (Fetched from AIClient globally)
TEMPERATURE = 0.2

# API Timeouts
SEARCH_TIMEOUT = 10
SCRAPE_TIMEOUT = 15
