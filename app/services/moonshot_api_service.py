from datetime import datetime, timezone
from typing import Any

from slugify import slugify

from app.integrations.moonshot.api_adapter import MoonshotApiAdapter

OXO_PREFIX = "Oxo"


def _is_oxo_recipe_id(value: str | None) -> bool:
    return bool(value and value.startswith(f"{OXO_PREFIX}-"))


def _is_oxo_id(value: str | None) -> bool:
    return bool(value and value.startswith(f"{OXO_PREFIX}-"))


class MoonshotApiService:
    """Moonshot 业务服务层，后续业务规则、审计日志、权限校验都放这里。"""

    def __init__(self, adapter: MoonshotApiAdapter | None = None) -> None:
        self.adapter = adapter or MoonshotApiAdapter()

    # 连接器
    def create_connector_from_endpoint(self, ep_id: str) -> Any:
        """根据端点 ID 创建连接器。"""
        return self.adapter.create_connector_from_endpoint(ep_id)

    def create_connectors_from_endpoints(self, ep_ids: list[str]) -> Any:
        """根据端点 ID 列表批量创建连接器。"""
        return self.adapter.create_connectors_from_endpoints(ep_ids)

    def get_all_connector_type(self) -> list[str]:
        """获取所有可用连接器类型。"""
        return self.adapter.get_all_connector_type()

    # 端点
    def create_endpoint(self, data: dict[str, Any]) -> str:
        """创建模型或应用端点。"""
        return self.adapter.create_endpoint(data)

    def delete_endpoint(self, ep_id: str) -> bool:
        """删除端点。"""
        return self.adapter.delete_endpoint(ep_id)

    def get_all_endpoint(self) -> list[dict]:
        """获取全部端点详情。"""
        return self.adapter.get_all_endpoint()

    def get_all_endpoint_name(self) -> list[str]:
        """获取全部端点名称。"""
        return self.adapter.get_all_endpoint_name()

    def read_endpoint(self, ep_id: str) -> dict:
        """读取端点详情。"""
        return self.adapter.read_endpoint(ep_id)

    def update_endpoint(self, ep_id: str, data: dict[str, Any]) -> bool:
        """更新端点配置。"""
        return self.adapter.update_endpoint(ep_id, data)

    # 上下文策略
    def delete_context_strategy(self, cs_id: str) -> bool:
        """删除上下文策略。"""
        return self.adapter.delete_context_strategy(cs_id)

    def get_all_context_strategies(self) -> list[str]:
        """获取全部上下文策略名称。"""
        return self.adapter.get_all_context_strategies()

    def get_all_context_strategy_metadata(self) -> list[dict]:
        """获取全部上下文策略元数据。"""
        return self.adapter.get_all_context_strategy_metadata()

    # Cookbook
    def create_cookbook(self, name: str, description: str, recipes: list[str]) -> str:
        """创建 cookbook。"""
        return self.adapter.create_cookbook(name, description, recipes)

    def delete_cookbook(self, cb_id: str) -> bool:
        """删除 cookbook。"""
        return self.adapter.delete_cookbook(cb_id)

    def get_all_cookbook(self) -> list[dict]:
        """获取全部 cookbook。"""
        return self.adapter.get_all_cookbook()

    def get_all_cookbook_name(self) -> list[str]:
        """获取全部 cookbook 名称。"""
        return self.adapter.get_all_cookbook_name()

    def read_cookbook(self, cb_id: str) -> dict:
        """读取 cookbook。"""
        return self.adapter.read_cookbook(cb_id)

    def read_cookbooks(self, cb_ids: list[str]) -> list[dict]:
        """批量读取 cookbook。"""
        return self.adapter.read_cookbooks(cb_ids)

    def update_cookbook(self, cb_id: str, data: dict[str, Any]) -> bool:
        """更新 cookbook。"""
        return self.adapter.update_cookbook(cb_id, data)

    # 数据集
    def convert_dataset(self, data: dict[str, Any]) -> str:
        """转换 CSV 数据集为 Moonshot 数据集。"""
        return self.adapter.convert_dataset(data)

    def download_dataset(self, data: dict[str, Any]) -> str:
        """下载并创建数据集。"""
        return self.adapter.download_dataset(data)

    def delete_dataset(self, ds_id: str) -> bool:
        """删除数据集。"""
        if not _is_oxo_recipe_id(ds_id):
            raise ValueError("Only datasets stored with Oxo-prefixed file IDs can be deleted.")
        return self.adapter.delete_dataset(ds_id)

    def get_all_datasets(self) -> list[dict]:
        """获取全部数据集。"""
        return self.adapter.get_all_datasets()

    def get_all_datasets_name(self) -> list[str]:
        """获取全部数据集名称。"""
        return self.adapter.get_all_datasets_name()

    def create_dataset(self, data: dict[str, Any]) -> str:
        """创建 Oxo 数据集。"""
        if not str(data.get("name", "")).strip():
            raise ValueError("Dataset name is required.")
        examples = data.get("examples") or []
        if not examples:
            raise ValueError("At least one dataset example is required.")
        for example in examples:
            if not str(example.get("input", "")).strip() or not str(example.get("target", "")).strip():
                raise ValueError("Every dataset example must include input and target.")
        slug = slugify(data["name"], lowercase=True) or datetime.now(timezone.utc).strftime("dataset-%Y%m%d%H%M%S")
        data["id"] = f"{OXO_PREFIX}-{slug}"
        data.setdefault("reference", "Oxo Tracker")
        data.setdefault("license", "Internal")
        data["examples"] = iter(examples)
        return self.adapter.create_dataset(data)

    def read_dataset(self, ds_id: str, limit: int = 25, offset: int = 0) -> dict:
        """读取数据集详情。"""
        return self.adapter.read_dataset(ds_id, limit, offset)

    def update_dataset(self, ds_id: str, data: dict[str, Any]) -> bool:
        """更新 Oxo 数据集。"""
        if not _is_oxo_recipe_id(ds_id):
            raise ValueError("Only datasets stored with Oxo-prefixed file IDs can be edited.")
        examples = data.get("examples") or []
        if not examples:
            raise ValueError("At least one dataset example is required.")
        for example in examples:
            if not str(example.get("input", "")).strip() or not str(example.get("target", "")).strip():
                raise ValueError("Every dataset example must include input and target.")
        return self.adapter.update_dataset(ds_id, data)

    # 环境变量
    def set_environment_variables(self, env_vars: dict[str, Any]) -> None:
        """设置 Moonshot 环境变量。"""
        return self.adapter.set_environment_variables(env_vars)

    # 指标
    def delete_metric(self, met_id: str) -> bool:
        """删除指标。"""
        return self.adapter.delete_metric(met_id)

    def get_all_metric(self) -> list[dict]:
        """获取全部指标。"""
        return self.adapter.get_all_metric()

    def get_all_metric_name(self) -> list[str]:
        """获取全部指标名称。"""
        return self.adapter.get_all_metric_name()

    # Prompt 模板
    def get_all_prompt_template_detail(self) -> list[dict]:
        """获取全部 Prompt 模板详情。"""
        return self.adapter.get_all_prompt_template_detail()

    def get_all_prompt_template_name(self) -> list[str]:
        """获取全部 Prompt 模板名称。"""
        return self.adapter.get_all_prompt_template_name()

    def create_prompt_template(self, data: dict[str, Any]) -> str:
        """Create an Oxo-owned prompt template."""
        name = str(data.get("name", "")).strip()
        template = str(data.get("template", "")).strip()
        if not name:
            raise ValueError("Prompt template name is required.")
        if "{{ prompt }}" not in template and "{{prompt}}" not in template:
            raise ValueError("Prompt template must include a {{ prompt }} block.")
        slug = slugify(name, lowercase=True) or datetime.now(timezone.utc).strftime("prompt-template-%Y%m%d%H%M%S")
        data["id"] = f"{OXO_PREFIX}-{slug}"
        data["name"] = name
        data["description"] = str(data.get("description", "")).strip()
        data["template"] = template
        return self.adapter.create_prompt_template(data)

    def delete_prompt_template(self, pt_id: str) -> bool:
        """删除 Prompt 模板。"""
        if not _is_oxo_id(pt_id):
            raise ValueError("Only Oxo prompt templates can be deleted.")
        return self.adapter.delete_prompt_template(pt_id)

    # Recipe
    def create_recipe(self, data: dict[str, Any]) -> str:
        """创建 recipe。"""
        if not str(data.get("name", "")).strip():
            raise ValueError("Recipe name is required.")
        if len(data.get("metrics") or []) > 1:
            raise ValueError("Recipes can use at most one metric.")
        if len(data.get("metrics") or []) < 1:
            raise ValueError("Recipe metric is required.")
        if len(data.get("prompt_templates") or []) > 1:
            raise ValueError("Recipes can use at most one prompt template.")
        slug = slugify(data["name"], lowercase=True) or datetime.now(timezone.utc).strftime("recipe-%Y%m%d%H%M%S")
        data["id"] = f"{OXO_PREFIX}-{slug}"
        return self.adapter.create_recipe(data)

    def delete_recipe(self, rec_id: str) -> bool:
        """删除 recipe。"""
        if not _is_oxo_recipe_id(rec_id):
            raise ValueError("Only recipes stored with Oxo-prefixed file IDs can be deleted.")
        return self.adapter.delete_recipe(rec_id)

    def get_all_recipe(self) -> list[dict]:
        """获取全部 recipe。"""
        return self.adapter.get_all_recipe()

    def get_all_recipe_name(self) -> list[str]:
        """获取全部 recipe 名称。"""
        return self.adapter.get_all_recipe_name()

    def read_recipe(self, rec_id: str) -> dict:
        """读取 recipe。"""
        return self.adapter.read_recipe(rec_id)

    def read_recipes(self, rec_ids: list[str]) -> list[dict]:
        """批量读取 recipe。"""
        return self.adapter.read_recipes(rec_ids)

    def update_recipe(self, rec_id: str, data: dict[str, Any]) -> bool:
        """更新 recipe。"""
        if not _is_oxo_recipe_id(rec_id):
            raise ValueError("Only recipes stored with Oxo-prefixed file IDs can be edited.")
        if len(data.get("metrics") or []) > 1:
            raise ValueError("Recipes can use at most one metric.")
        if "metrics" in data and len(data.get("metrics") or []) < 1:
            raise ValueError("Recipe metric is required.")
        if len(data.get("prompt_templates") or []) > 1:
            raise ValueError("Recipes can use at most one prompt template.")
        return self.adapter.update_recipe(rec_id, data)

    # 攻击模块
    def get_all_attack_module_metadata(self) -> list[dict]:
        """获取全部攻击模块元数据。"""
        return self.adapter.get_all_attack_module_metadata()

    def get_all_attack_modules(self) -> list[str]:
        """获取全部攻击模块名称。"""
        return self.adapter.get_all_attack_modules()

    def delete_attack_module(self, am_id: str) -> bool:
        """删除攻击模块。"""
        return self.adapter.delete_attack_module(am_id)

    # 结果
    def delete_result(self, res_id: str) -> bool:
        """删除测试结果。"""
        return self.adapter.delete_result(res_id)

    def get_all_result(self) -> list[dict]:
        """获取全部测试结果。"""
        return self.adapter.get_all_result()

    def get_all_result_name(self) -> list[str]:
        """获取全部测试结果名称。"""
        return self.adapter.get_all_result_name()

    def read_result(self, res_id: str) -> dict:
        """读取测试结果。"""
        return self.adapter.read_result(res_id)

    def read_results(self, res_ids: list[str]) -> list[dict]:
        """批量读取测试结果。"""
        return self.adapter.read_results(res_ids)

    # Run / Runner
    def get_all_run(self, runner_id: str = "") -> list[dict]:
        """获取运行记录。"""
        return self.adapter.get_all_run(runner_id)

    def create_runner(self, name: str, endpoints: list[str], description: str = "") -> Any:
        """创建 runner。"""
        return self.adapter.create_runner(name, endpoints, description)

    def delete_runner(self, runner_id: str) -> bool:
        """删除 runner。"""
        return self.adapter.delete_runner(runner_id)

    def get_all_runner(self) -> list[dict]:
        """获取全部 runner。"""
        return self.adapter.get_all_runner()

    def get_all_runner_name(self) -> list[str]:
        """获取全部 runner 名称。"""
        return self.adapter.get_all_runner_name()

    def load_runner(self, runner_id: str) -> Any:
        """加载 runner。"""
        return self.adapter.load_runner(runner_id)

    def read_runner(self, runner_id: str) -> dict:
        """读取 runner。"""
        return self.adapter.read_runner(runner_id)

    # Session
    def create_session(
        self, runner_id: str, database_instance: Any, endpoints: list[str], runner_args: dict
    ) -> Any:
        """创建 red teaming session。"""
        return self.adapter.create_session(runner_id, database_instance, endpoints, runner_args)

    def prepare_redteam_prompt(
        self,
        prompt: str,
        prompt_template: str = "",
        attack_module: str = "",
    ) -> dict[str, str]:
        """Prepare the exact prompt that will be sent from the chat UI."""
        if not prompt.strip():
            return {
                "original_prompt": "",
                "templated_prompt": "",
                "prepared_prompt": "",
                "prompt_template": prompt_template,
                "attack_module": attack_module,
            }
        return self.adapter.prepare_redteam_prompt(prompt, prompt_template, attack_module)

    def create_redteam_session(
        self,
        name: str,
        endpoints: list[str],
        description: str = "",
        runner_args: dict | None = None,
    ) -> dict:
        """Create a red-team session through a new Moonshot runner."""
        return self.adapter.create_redteam_session(name, endpoints, description, runner_args or {})

    async def send_redteam_prompt(self, runner_id: str, user_prompt: str, prepared_prompt: str = "") -> Any:
        """Send a prompt to a red-team session."""
        if not user_prompt.strip():
            raise ValueError("Prompt is required.")
        return await self.adapter.send_redteam_prompt(runner_id, user_prompt.strip(), prepared_prompt.strip())

    def delete_session(self, runner_id: str) -> bool:
        """删除 red teaming session。"""
        return self.adapter.delete_session(runner_id)

    def get_all_chats_from_session(self, runner_id: str) -> dict | None:
        """获取 session 聊天记录。"""
        return self.adapter.get_all_chats_from_session(runner_id)

    def get_all_session_metadata(self) -> list[dict]:
        """获取全部 session 元数据。"""
        return self.adapter.get_all_session_metadata()

    def get_all_session_names(self) -> list[str]:
        """获取全部 session 名称。"""
        return self.adapter.get_all_session_names()

    def get_available_session_info(self) -> Any:
        """获取可用 session 信息。"""
        return self.adapter.get_available_session_info()

    def load_session(self, runner_id: str) -> dict | None:
        """加载 session。"""
        return self.adapter.load_session(runner_id)

    def update_attack_module(self, runner_id: str, attack_module_id: str) -> bool:
        """更新 session 攻击模块。"""
        return self.adapter.update_attack_module(runner_id, attack_module_id)

    def update_context_strategy(self, runner_id: str, context_strategy: str) -> bool:
        """更新 session 上下文策略。"""
        return self.adapter.update_context_strategy(runner_id, context_strategy)

    def update_cs_num_of_prev_prompts(self, runner_id: str, num_of_prev_prompts: int) -> bool:
        """更新上下文策略历史 prompt 数量。"""
        return self.adapter.update_cs_num_of_prev_prompts(runner_id, num_of_prev_prompts)

    def update_metric(self, runner_id: str, metric_id: str) -> bool:
        """更新 session 指标。"""
        return self.adapter.update_metric(runner_id, metric_id)

    def update_prompt_template(self, runner_id: str, prompt_template: str) -> bool:
        """更新 session Prompt 模板。"""
        return self.adapter.update_prompt_template(runner_id, prompt_template)

    def update_system_prompt(self, runner_id: str, system_prompt: str) -> bool:
        """更新 session 系统提示词。"""
        return self.adapter.update_system_prompt(runner_id, system_prompt)

    # Bookmark
    def get_all_bookmarks(self) -> list[dict]:
        """获取全部书签。"""
        return self.adapter.get_all_bookmarks()

    def get_bookmark(self, bookmark_name: str) -> dict:
        """读取书签。"""
        return self.adapter.get_bookmark(bookmark_name)

    def insert_bookmark(self, data: dict[str, Any]) -> dict:
        """新增书签。"""
        return self.adapter.insert_bookmark(data)

    def delete_bookmark(self, bookmark_name: str) -> dict:
        """删除书签。"""
        return self.adapter.delete_bookmark(bookmark_name)

    def delete_all_bookmark(self) -> dict:
        """删除全部书签。"""
        return self.adapter.delete_all_bookmark()

    def export_bookmarks(self, export_file_name: str = "bookmarks") -> str:
        """导出书签。"""
        return self.adapter.export_bookmarks(export_file_name)
