import asyncio

from app.integrations.moonshot import client as moonshot_client


class _OldRunner:
    def __init__(self) -> None:
        self.id = "runner-old"
        self.calls: list[dict] = []
        self.current_operation = None
        self.current_operation_lock = asyncio.Lock()
        self.database_instance = None
        self.endpoints = ["endpoint-1"]
        self.progress_callback_func = None

    async def run_cookbooks(
        self,
        cookbooks,
        prompt_selection_percentage=100,
        random_seed=0,
        system_prompt="",
    ) -> None:
        self.calls.append(
            {
                "cookbooks": cookbooks,
                "prompt_selection_percentage": prompt_selection_percentage,
                "random_seed": random_seed,
                "system_prompt": system_prompt,
            }
        )


class _NewRunner(_OldRunner):
    async def run_cookbooks(
        self,
        cookbooks,
        prompt_selection_percentage=100,
        cookbook_prompt_selection_percentages=None,
        random_seed=0,
        system_prompt="",
    ) -> None:
        self.calls.append(
            {
                "cookbooks": cookbooks,
                "prompt_selection_percentage": prompt_selection_percentage,
                "cookbook_prompt_selection_percentages": cookbook_prompt_selection_percentages,
                "random_seed": random_seed,
                "system_prompt": system_prompt,
            }
        )


def _client_without_initialization() -> moonshot_client.MoonshotClient:
    return object.__new__(moonshot_client.MoonshotClient)


def test_official_runner_without_extended_argument_uses_native_call_when_map_is_empty(monkeypatch) -> None:
    runner = _OldRunner()
    monkeypatch.setattr(moonshot_client, "api_create_runner", lambda **_kwargs: runner)

    result = asyncio.run(
        _client_without_initialization().run_cookbooks(
            run_name="test-run",
            endpoints=["endpoint-1"],
            cookbooks=["data-disclosure"],
            prompt_selection_percentage=75,
        )
    )

    assert result == {"runner_id": "runner-old", "status": "completed"}
    assert runner.calls == [
        {
            "cookbooks": ["data-disclosure"],
            "prompt_selection_percentage": 75,
            "random_seed": 0,
            "system_prompt": "",
        }
    ]


def test_official_runner_receives_extended_map_through_product_compatibility_run(monkeypatch) -> None:
    runner = _OldRunner()
    captured = {}

    class _FakeRun:
        def __init__(self, runner_id, runner_type, runner_args, database, endpoints, results_file, progress_callback) -> None:
            captured.update(
                runner_id=runner_id,
                runner_type=runner_type,
                runner_args=runner_args,
                database=database,
                endpoints=endpoints,
                results_file=results_file,
                progress_callback=progress_callback,
            )

        async def run(self) -> None:
            captured["ran"] = True

    class _FakeStorage:
        @staticmethod
        def get_filepath(*_args):
            return "results.json"

    monkeypatch.setattr(moonshot_client, "api_create_runner", lambda **_kwargs: runner)
    monkeypatch.setattr(moonshot_client, "Run", _FakeRun)
    monkeypatch.setattr(moonshot_client, "Storage", _FakeStorage)

    asyncio.run(
        _client_without_initialization().run_cookbooks(
            run_name="test-run",
            endpoints=["endpoint-1"],
            cookbooks=["data-disclosure", "toxicity"],
            prompt_selection_percentage=100,
            cookbook_prompt_selection_percentages={"data-disclosure": 25, "toxicity": 80},
            random_seed=7,
            system_prompt="system",
        )
    )

    assert captured["ran"] is True
    assert captured["runner_args"] == {
        "cookbooks": ["data-disclosure", "toxicity"],
        "prompt_selection_percentage": 100,
        "cookbook_prompt_selection_percentages": {"data-disclosure": 25, "toxicity": 80},
        "random_seed": 7,
        "system_prompt": "system",
        "runner_processing_module": "benchmarking",
        "result_processing_module": "benchmarking-result",
    }
    assert runner.calls == []
    assert runner.current_operation is None


def test_extended_runner_continues_to_receive_per_cookbook_percentages(monkeypatch) -> None:
    runner = _NewRunner()
    monkeypatch.setattr(moonshot_client, "api_create_runner", lambda **_kwargs: runner)

    asyncio.run(
        _client_without_initialization().run_cookbooks(
            run_name="test-run",
            endpoints=["endpoint-1"],
            cookbooks=["data-disclosure"],
            cookbook_prompt_selection_percentages={"data-disclosure": 40},
        )
    )

    assert runner.calls[0]["cookbook_prompt_selection_percentages"] == {"data-disclosure": 40}
