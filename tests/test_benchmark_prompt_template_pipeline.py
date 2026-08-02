import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "moonshot-data"
    / "runners-modules"
    / "benchmarking.py"
)


def _load_benchmarking_module():
    spec = importlib.util.spec_from_file_location("oxo_benchmarking_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_each_dataset_row_is_rendered_by_the_selected_prompt_template(monkeypatch) -> None:
    module = _load_benchmarking_module()
    runner = module.Benchmarking()
    runner.recipe_instance = SimpleNamespace(
        id="recipe-one",
        datasets=["dataset-one", "dataset-two"],
        prompt_templates=["template-one"],
    )
    runner.random_seed = 7
    runner.system_prompt = ""

    template_reads: list[tuple[str, str, str]] = []

    def fake_read_object_with_iterator(resource, asset_id, extension, **_kwargs):
        template_reads.append((resource, asset_id, extension))
        return {"template": iter(["Safety test:\n{{ prompt }}"])}

    rows = {
        "dataset-one": [
            (0, {"input": "first row", "target": "safe"}),
            (1, {"input": "second row", "target": "safe"}),
        ],
        "dataset-two": [(0, {"input": "third row", "target": "safe"})],
    }

    async def fake_get_dataset_prompts(dataset_id):
        for row in rows[dataset_id]:
            yield row

    monkeypatch.setattr(
        module.Storage,
        "read_object_with_iterator",
        staticmethod(fake_read_object_with_iterator),
    )
    runner._get_dataset_prompts = fake_get_dataset_prompts

    async def collect_prompts():
        return [item async for item in runner._generate_prompts()]

    generated = asyncio.run(collect_prompts())

    assert template_reads == [
        (module.EnvVariables.PROMPT_TEMPLATES.name, "template-one", "json")
    ]
    assert [item.ds_id for item in generated] == [
        "dataset-one",
        "dataset-one",
        "dataset-two",
    ]
    assert [item.pt_id for item in generated] == ["template-one"] * 3
    assert [item.connector_prompt.prompt for item in generated] == [
        "Safety test:\nfirst row",
        "Safety test:\nsecond row",
        "Safety test:\nthird row",
    ]
    assert [item.connector_prompt.target for item in generated] == ["safe"] * 3
