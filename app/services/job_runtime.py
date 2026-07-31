import asyncio
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunnerRegistration:
    runner: Any
    loop: asyncio.AbstractEventLoop


class JobRuntime:
    def __init__(self) -> None:
        self._runners: dict[str, RunnerRegistration] = {}
        self._lock = threading.Lock()

    async def register(self, job_id: str, runner: Any) -> None:
        registration = RunnerRegistration(runner=runner, loop=asyncio.get_running_loop())
        with self._lock:
            self._runners[job_id] = registration

    async def unregister(self, job_id: str) -> None:
        with self._lock:
            self._runners.pop(job_id, None)

    async def cancel(self, job_id: str) -> bool:
        with self._lock:
            registration = self._runners.get(job_id)
        if not registration:
            return False
        cancel = getattr(registration.runner, "cancel", None)
        if not cancel:
            return False

        current_loop = asyncio.get_running_loop()
        if registration.loop is current_loop:
            await self._invoke_cancel(cancel)
            return True
        if registration.loop.is_closed():
            return False

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._invoke_cancel(cancel),
                registration.loop,
            )
        except RuntimeError:
            return False
        future.add_done_callback(self._consume_cancel_result)
        return True

    async def _invoke_cancel(self, cancel: Any) -> None:
        result = cancel()
        if hasattr(result, "__await__"):
            await result

    @staticmethod
    def _consume_cancel_result(future: Any) -> None:
        try:
            future.result()
        except BaseException:
            pass


job_runtime = JobRuntime()
