import asyncio
import time

from app.services.benchmark_service import BenchmarkService


class BlockingBenchmarkService(BenchmarkService):
    def __init__(self) -> None:
        self.executed_job_id: str | None = None

    async def execute_recipe_job(self, job_id: str) -> None:
        time.sleep(0.15)
        self.executed_job_id = job_id


def test_background_benchmark_does_not_block_the_api_event_loop() -> None:
    service = BlockingBenchmarkService()

    async def scenario() -> None:
        task = asyncio.create_task(service.execute_recipe_job_background("job-1"))
        started = asyncio.get_running_loop().time()

        await asyncio.sleep(0.02)

        assert asyncio.get_running_loop().time() - started < 0.1
        assert not task.done()
        await task

    asyncio.run(scenario())

    assert service.executed_job_id == "job-1"
