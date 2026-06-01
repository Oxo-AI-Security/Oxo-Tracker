import asyncio
from typing import Any


class JobRuntime:
    def __init__(self) -> None:
        self._runners: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def register(self, job_id: str, runner: Any) -> None:
        async with self._lock:
            self._runners[job_id] = runner

    async def unregister(self, job_id: str) -> None:
        async with self._lock:
            self._runners.pop(job_id, None)

    async def cancel(self, job_id: str) -> bool:
        async with self._lock:
            runner = self._runners.get(job_id)
        if not runner:
            return False
        cancel = getattr(runner, "cancel", None)
        if not cancel:
            return False
        result = cancel()
        if hasattr(result, "__await__"):
            await result
        return True


job_runtime = JobRuntime()
