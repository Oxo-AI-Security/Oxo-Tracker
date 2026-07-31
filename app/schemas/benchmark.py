from pydantic import BaseModel, Field


class BenchmarkRecipeRequest(BaseModel):
    run_name: str = Field(min_length=1)
    endpoints: list[str] = Field(min_length=1)
    recipes: list[str] = Field(min_length=1)
    cookbooks: list[str] = []
    evaluator_provider: str | None = None
    evaluator_model: str | None = None
    evaluator_endpoints: list[str] = Field(default_factory=list)
    cookbook_prompt_selection_percentages: dict[str, int] = Field(default_factory=dict)
    description: str = ""
    prompt_selection_percentage: int = Field(default=100, ge=1, le=100)
    estimated_prompts: int = Field(default=0, ge=0)
    thread_count: int = Field(default=4, ge=1, le=20)
    random_seed: int = 0
    system_prompt: str = ""


class BenchmarkRunResponse(BaseModel):
    runner_id: str
    status: str
