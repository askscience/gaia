import threading
from src.core.config import ConfigManager
from src.core.concurrency.limits import get_limit_for_provider
from src.core.concurrency.primitives import AsyncThreadingSemaphore

class ConcurrencyManager:
    """
    Singleton manager for global concurrency limits.
    Ensures all tools share the same token bucket (Semaphore) depending on the active provider.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConcurrencyManager, cls).__new__(cls)
                cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.config = ConfigManager()
        self._provider_semaphores = {} # Cache for provider semaphores
        self._current_provider = None
        self._current_semaphore = None
        
        # Load initially
        self._refresh_semaphore()

    def _refresh_semaphore(self):
        """Check config and update current semaphore if provider changed."""
        provider = self.config.get("provider", "ollama")
        
        if provider != self._current_provider:
            print(f"[ConcurrencyManager] Switching provider to {provider}")
            self._current_provider = provider
            
            if provider not in self._provider_semaphores:
                limit = get_limit_for_provider(provider)
                print(f"[ConcurrencyManager] Initializing semaphore for {provider} with limit {limit}")
                self._provider_semaphores[provider] = threading.Semaphore(limit)
                
            self._current_semaphore = self._provider_semaphores[provider]

    def get_async_semaphore(self) -> AsyncThreadingSemaphore:
        """
        Returns an async context manager that acquires the GLOBAL semaphore
        for the current provider.
        """
        # We check for config changes lazily
        current_conf_provider = self.config.get("provider", "ollama")
        if current_conf_provider != self._current_provider:
            with self._lock:
                 self._refresh_semaphore()
                 
        return AsyncThreadingSemaphore(self._current_semaphore)
