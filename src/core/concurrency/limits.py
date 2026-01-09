"""
Default concurrency limits for different AI providers.
Used to prevent 429 Too Many Requests errors.
"""

# Default safety limit
DEFAULT_LIMIT = 5

# Provider-specific limits (Conservative defaults)
# These can be overridden if we implement a tiered config later.
PROVIDER_LIMITS = {
    "zai": 2,          # Strict concurrency limit for GLM-4.7
    "ollama": 4,       # Local inference (VRAM limited)
    "openai": 8,       # Tier 1 approx limit. Higher tiers can handle 50+
    "anthropic": 4,    # Tier 1 concurrent limit is often tight
    "google": 5,       # Gemini Free tier approx
    "mistral": 4,      # Mistral La Plateforme conservative limit
    "deepseek": 5,     # Unofficial practical limit
    "groq": 5,         # Fast inference but often rate-limited
}

def get_limit_for_provider(provider_name: str) -> int:
    """Get the safe concurrency limit for a given provider."""
    # Normalize keys (e.g. 'gemini' -> 'google')
    key = provider_name.lower()
    if key == "gemini": key = "google"
    return PROVIDER_LIMITS.get(key, DEFAULT_LIMIT)
