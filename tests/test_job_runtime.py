import asyncio
import threading

from app.services.job_runtime import JobRuntime


class CancellableRunner:
    def __init__(self) -> None:
        self.cancelled = threading.Event()

    async def cancel(self) -> None:
        self.cancelled.set()


def test_cancel_is_scheduled_on_the_runner_worker_loop() -> None:
    runtime = JobRuntime()
    runner = CancellableRunner()
    registered = threading.Event()
    release_worker = threading.Event()

    async def worker() -> None:
        await runtime.register("job-1", runner)
        registered.set()
        while not release_worker.is_set():
            await asyncio.sleep(0.005)
        await runtime.unregister("job-1")

    thread = threading.Thread(target=lambda: asyncio.run(worker()), daemon=True)
    thread.start()
    assert registered.wait(timeout=1)

    assert asyncio.run(runtime.cancel("job-1")) is True
    assert runner.cancelled.wait(timeout=1)

    release_worker.set()
    thread.join(timeout=1)
    assert not thread.is_alive()
