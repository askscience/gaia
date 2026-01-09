import asyncio
import threading

class AsyncThreadingSemaphore:
    """
    An asyncio-compatible wrapper around a threading.Semaphore.
    Allows limiting concurrency across multiple event loops and threads globally.
    """
    def __init__(self, semaphore: threading.Semaphore):
        self._sem = semaphore

    async def __aenter__(self):
        # Acquire the semaphore in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sem.acquire)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._sem.release()
