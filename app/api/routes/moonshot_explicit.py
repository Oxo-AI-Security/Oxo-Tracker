import json
import shutil
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Body, HTTPException

from app.services.moonshot_api_service import MoonshotApiService

router = APIRouter(prefix="/moonshot", tags=["Moonshot Explicit API"])
REDTEAM_DATA_DIR = Path("data/redteam_sessions")


def service() -> MoonshotApiService:
    """创建 Moonshot 服务实例，后续可替换成依赖注入容器。"""
    return MoonshotApiService()


def _redteam_session_path(session_id: str) -> Path:
    safe_id = "".join(char for char in session_id if char.isalnum() or char in ("-", "_"))[:120]
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid session id.")
    return REDTEAM_DATA_DIR / safe_id / "session.json"


@router.get("/redteam/local-sessions", summary="List persisted red-team chat sessions")
def list_local_redteam_sessions():
    REDTEAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for session_file in sorted(REDTEAM_DATA_DIR.glob("*/session.json")):
        try:
            sessions.append(json.loads(session_file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sessions


@router.put("/redteam/local-sessions/{session_id}", summary="Persist a red-team chat session")
def save_local_redteam_session(session_id: str, data: dict[str, Any] = Body(...)):
    path = _redteam_session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**data, "id": session_id}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "session_id": session_id}


@router.delete("/redteam/local-sessions/{session_id}", summary="Delete a persisted red-team chat session")
def delete_local_redteam_session(session_id: str):
    path = _redteam_session_path(session_id)
    if path.parent.exists():
        shutil.rmtree(path.parent)
    return {"deleted": True, "session_id": session_id}


def handle_call(callable_result):
    """统一处理 Moonshot 异常，避免原始异常直接泄漏到接口层。"""
    try:
        return callable_result()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# 连接器
@router.post("/connectors/from-endpoint", summary="根据端点创建连接器")
def create_connector_from_endpoint(ep_id: str = Body(..., embed=True)):
    """根据端点 ID 创建连接器，通常用于调试 endpoint 是否能加载。"""
    return handle_call(lambda: service().create_connector_from_endpoint(ep_id))


@router.post("/connectors/from-endpoints", summary="批量根据端点创建连接器")
def create_connectors_from_endpoints(ep_ids: list[str] = Body(..., embed=True)):
    """根据多个端点 ID 批量创建连接器。"""
    return handle_call(lambda: service().create_connectors_from_endpoints(ep_ids))


@router.get("/connectors/types", summary="获取全部连接器类型")
def get_all_connector_type():
    """获取当前 moonshot-data 中可用的连接器类型。"""
    return handle_call(lambda: service().get_all_connector_type())


# 端点
@router.post("/connectors/test", summary="Test configurable connector endpoint")
def test_connector(data: dict[str, Any] = Body(...)):
    config = data.get("config") or {}
    prompt = data.get("test_prompt") or "Hello"
    started = time.perf_counter()
    try:
        params = config.get("params") or {}
        connector_config = params.get("connector_config") or {}
        request_config = connector_config.get("request") or connector_config.get("stream") or connector_config.get("websocket") or {}
        url = str(config.get("uri") or "")
        if not url:
            raise ValueError("Request URL is required.")
        body_template = request_config.get("bodyTemplate") or request_config.get("messageTemplate") or '{"prompt":"{{ prompt }}"}'
        body = body_template.replace("{{ prompt }}", str(prompt)).replace("{{prompt}}", str(prompt)).encode("utf-8")
        headers = dict(request_config.get("headers") or {})
        auth = connector_config.get("auth") or {}
        token = str(config.get("token") or "")
        if auth.get("type") == "bearer" and token:
            headers[auth.get("headerName") or "Authorization"] = f"Bearer {token}"
        if auth.get("type") == "api-key" and token:
            headers[auth.get("headerName") or "x-api-key"] = token
        if auth.get("type") == "cookie" and token:
            headers[auth.get("headerName") or "Cookie"] = token
        method = request_config.get("method") or "POST"
        req = urllib_request.Request(url, data=body, headers=headers, method=method)
        timeout = max(1, min(120, int((params.get("timeout") or 30000) / 1000)))
        with urllib_request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status_code = response.status
        extracted = _extract_connector_response(raw, connector_config.get("response") or {})
        return {
            "status": "success",
            "duration": round((time.perf_counter() - started) * 1000),
            "requestPreview": json.dumps({"url": url, "method": method, "headers": _mask_headers(headers), "body": body.decode("utf-8")}, indent=2),
            "rawResponse": raw,
            "extractedResponse": extracted,
            "httpStatus": status_code,
        }
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "duration": round((time.perf_counter() - started) * 1000), "requestPreview": json.dumps({"url": config.get("uri"), "error": "HTTP error"}, indent=2), "rawResponse": raw, "extractedResponse": "", "error": f"HTTP {exc.code}: {exc.reason}"}
    except (URLError, ValueError, TimeoutError) as exc:
        return {"status": "error", "duration": round((time.perf_counter() - started) * 1000), "requestPreview": json.dumps({"url": config.get("uri")}, indent=2), "rawResponse": "", "extractedResponse": "", "error": str(exc)}


def _extract_connector_response(raw: str, response_config: dict[str, Any]) -> str:
    if response_config.get("type") == "text":
        return raw
    if response_config.get("type") == "event-data":
        for line in raw.splitlines():
            if line.startswith("data:"):
                return line.replace("data:", "", 1).strip()
        return raw
    try:
        parsed = json.loads(raw)
    except Exception:
        return raw
    for path in (response_config.get("path"), response_config.get("fallbackPath")):
        if not path:
            continue
        value = _read_json_path(parsed, path)
        if value is not None:
            return str(value)
    return ""


def _read_json_path(data: Any, path: str) -> Any:
    current = data
    for part in path.replace("$.", "").split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def _mask_headers(headers: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if key.lower() in {"authorization", "cookie", "x-api-key"} else value) for key, value in headers.items()}


@router.post("/endpoints", summary="Create model endpoint")
def create_endpoint(data: dict[str, Any] = Body(...)):
    """创建模型或应用端点，body 字段对应 Moonshot 的 api_create_endpoint 参数。"""
    return handle_call(lambda: service().create_endpoint(data))


@router.delete("/endpoints/{ep_id}", summary="删除模型端点")
def delete_endpoint(ep_id: str):
    """根据端点 ID 删除模型端点。"""
    return handle_call(lambda: service().delete_endpoint(ep_id))


@router.get("/endpoints", summary="获取全部模型端点")
def get_all_endpoint():
    """获取全部已配置模型端点详情。"""
    return handle_call(lambda: service().get_all_endpoint())


@router.get("/endpoints/names", summary="获取全部模型端点名称")
def get_all_endpoint_name():
    """获取全部已配置模型端点 ID 列表。"""
    return handle_call(lambda: service().get_all_endpoint_name())


@router.get("/endpoints/{ep_id}", summary="读取模型端点")
def read_endpoint(ep_id: str):
    """根据端点 ID 读取端点详情。"""
    return handle_call(lambda: service().read_endpoint(ep_id))


@router.patch("/endpoints/{ep_id}", summary="更新模型端点")
def update_endpoint(ep_id: str, data: dict[str, Any] = Body(...)):
    """根据端点 ID 更新端点配置。"""
    return handle_call(lambda: service().update_endpoint(ep_id, data))


# 上下文策略
@router.delete("/context-strategies/{cs_id}", summary="删除上下文策略")
def delete_context_strategy(cs_id: str):
    """根据上下文策略 ID 删除策略。"""
    return handle_call(lambda: service().delete_context_strategy(cs_id))


@router.get("/context-strategies", summary="获取全部上下文策略")
def get_all_context_strategies():
    """获取全部 red teaming 上下文策略名称。"""
    return handle_call(lambda: service().get_all_context_strategies())


@router.get("/context-strategies/metadata", summary="获取上下文策略元数据")
def get_all_context_strategy_metadata():
    """获取全部上下文策略元数据。"""
    return handle_call(lambda: service().get_all_context_strategy_metadata())


# Cookbook
@router.post("/cookbooks", summary="创建 Cookbook")
def create_cookbook(
    name: str = Body(...),
    description: str = Body(""),
    recipes: list[str] = Body(...),
):
    """创建 cookbook，用于组合多个 recipe。"""
    return handle_call(lambda: service().create_cookbook(name, description, recipes))


@router.delete("/cookbooks/{cb_id}", summary="删除 Cookbook")
def delete_cookbook(cb_id: str):
    """根据 cookbook ID 删除 cookbook。"""
    return handle_call(lambda: service().delete_cookbook(cb_id))


@router.get("/cookbooks", summary="获取全部 Cookbook")
def get_all_cookbook():
    """获取全部 cookbook 详情。"""
    return handle_call(lambda: service().get_all_cookbook())


@router.get("/cookbooks/names", summary="获取全部 Cookbook 名称")
def get_all_cookbook_name():
    """获取全部 cookbook ID 列表。"""
    return handle_call(lambda: service().get_all_cookbook_name())


@router.get("/cookbooks/{cb_id}", summary="读取 Cookbook")
def read_cookbook(cb_id: str):
    """根据 cookbook ID 读取详情。"""
    return handle_call(lambda: service().read_cookbook(cb_id))


@router.post("/cookbooks/read-batch", summary="批量读取 Cookbook")
def read_cookbooks(cb_ids: list[str] = Body(..., embed=True)):
    """根据 cookbook ID 列表批量读取详情。"""
    return handle_call(lambda: service().read_cookbooks(cb_ids))


@router.patch("/cookbooks/{cb_id}", summary="更新 Cookbook")
def update_cookbook(cb_id: str, data: dict[str, Any] = Body(...)):
    """根据 cookbook ID 更新字段。"""
    return handle_call(lambda: service().update_cookbook(cb_id, data))


# 数据集
@router.post("/datasets/convert", summary="转换数据集")
def convert_dataset(data: dict[str, Any] = Body(...)):
    """将 CSV 数据集转换为 Moonshot 数据集。"""
    return handle_call(lambda: service().convert_dataset(data))


@router.post("/datasets/download", summary="下载数据集")
def download_dataset(data: dict[str, Any] = Body(...)):
    """下载外部数据集并创建 Moonshot 数据集。"""
    return handle_call(lambda: service().download_dataset(data))


@router.post("/datasets/read", summary="读取 Dataset")
def read_dataset_post(data: dict[str, Any] = Body(...)):
    ds_id = str(data.get("ds_id") or data.get("id") or "")
    limit = int(data.get("limit") or 25)
    offset = int(data.get("offset") or 0)
    return handle_call(lambda: service().read_dataset(ds_id, limit, offset))


@router.delete("/datasets/{ds_id}", summary="删除数据集")
def delete_dataset(ds_id: str):
    """根据数据集 ID 删除数据集。"""
    return handle_call(lambda: service().delete_dataset(ds_id))


@router.post("/datasets", summary="创建 Dataset")
def create_dataset(data: dict[str, Any] = Body(...)):
    return handle_call(lambda: service().create_dataset(data))


@router.get("/datasets", summary="获取全部数据集")
def get_all_datasets():
    """获取全部数据集详情。"""
    return handle_call(lambda: service().get_all_datasets())


@router.get("/datasets/names", summary="获取全部数据集名称")
def get_all_datasets_name():
    """获取全部数据集 ID 列表。"""
    return handle_call(lambda: service().get_all_datasets_name())


@router.get("/datasets/{ds_id}", summary="读取 Dataset")
def read_dataset(ds_id: str, limit: int = 25, offset: int = 0):
    return handle_call(lambda: service().read_dataset(ds_id, limit, offset))


@router.patch("/datasets/{ds_id}", summary="更新 Dataset")
def update_dataset(ds_id: str, data: dict[str, Any] = Body(...)):
    return handle_call(lambda: service().update_dataset(ds_id, data))


# 环境变量
@router.post("/environment", summary="设置 Moonshot 环境变量")
def set_environment_variables(env_vars: dict[str, Any] = Body(..., embed=True)):
    """设置 Moonshot 资源目录映射，通常启动时已自动完成。"""
    return handle_call(lambda: service().set_environment_variables(env_vars))


# 指标
@router.delete("/metrics/{met_id}", summary="删除评估指标")
def delete_metric(met_id: str):
    """根据 metric ID 删除评估指标。"""
    return handle_call(lambda: service().delete_metric(met_id))


@router.get("/metrics", summary="获取全部评估指标")
def get_all_metric():
    """获取全部评估指标详情。"""
    return handle_call(lambda: service().get_all_metric())


@router.get("/metrics/names", summary="获取全部评估指标名称")
def get_all_metric_name():
    """获取全部评估指标 ID 列表。"""
    return handle_call(lambda: service().get_all_metric_name())


# Prompt 模板
@router.get("/prompt-templates", summary="获取 Prompt 模板详情")
def get_all_prompt_template_detail():
    """获取全部 Prompt 模板详情。"""
    return handle_call(lambda: service().get_all_prompt_template_detail())


@router.get("/prompt-templates/names", summary="获取 Prompt 模板名称")
def get_all_prompt_template_name():
    """获取全部 Prompt 模板 ID 列表。"""
    return handle_call(lambda: service().get_all_prompt_template_name())


@router.post("/prompt-templates", summary="Create Prompt Template")
def create_prompt_template(data: dict[str, Any] = Body(...)):
    """Create an Oxo-owned prompt template."""
    return handle_call(lambda: service().create_prompt_template(data))


@router.delete("/prompt-templates/{pt_id}", summary="删除 Prompt 模板")
def delete_prompt_template(pt_id: str):
    """根据 Prompt 模板 ID 删除模板。"""
    return handle_call(lambda: service().delete_prompt_template(pt_id))


# Recipe
@router.post("/recipes", summary="创建 Recipe")
def create_recipe(data: dict[str, Any] = Body(...)):
    """创建 benchmark recipe。"""
    return handle_call(lambda: service().create_recipe(data))


@router.delete("/recipes/{rec_id}", summary="删除 Recipe")
def delete_recipe(rec_id: str):
    """根据 recipe ID 删除 recipe。"""
    return handle_call(lambda: service().delete_recipe(rec_id))


@router.get("/recipes", summary="获取全部 Recipe")
def get_all_recipe():
    """获取全部 recipe 详情。"""
    return handle_call(lambda: service().get_all_recipe())


@router.get("/recipes/names", summary="获取全部 Recipe 名称")
def get_all_recipe_name():
    """获取全部 recipe ID 列表。"""
    return handle_call(lambda: service().get_all_recipe_name())


@router.get("/recipes/{rec_id}", summary="读取 Recipe")
def read_recipe(rec_id: str):
    """根据 recipe ID 读取 recipe 详情。"""
    return handle_call(lambda: service().read_recipe(rec_id))


@router.post("/recipes/read-batch", summary="批量读取 Recipe")
def read_recipes(rec_ids: list[str] = Body(..., embed=True)):
    """根据 recipe ID 列表批量读取 recipe 详情。"""
    return handle_call(lambda: service().read_recipes(rec_ids))


@router.patch("/recipes/{rec_id}", summary="更新 Recipe")
def update_recipe(rec_id: str, data: dict[str, Any] = Body(...)):
    """根据 recipe ID 更新 recipe。"""
    return handle_call(lambda: service().update_recipe(rec_id, data))


# 攻击模块
@router.get("/attack-modules/metadata", summary="获取攻击模块元数据")
def get_all_attack_module_metadata():
    """获取全部 red teaming 攻击模块元数据。"""
    return handle_call(lambda: service().get_all_attack_module_metadata())


@router.get("/attack-modules", summary="获取全部攻击模块")
def get_all_attack_modules():
    """获取全部 red teaming 攻击模块名称。"""
    return handle_call(lambda: service().get_all_attack_modules())


@router.delete("/attack-modules/{am_id}", summary="删除攻击模块")
def delete_attack_module(am_id: str):
    """根据攻击模块 ID 删除攻击模块。"""
    return handle_call(lambda: service().delete_attack_module(am_id))


# 结果
@router.delete("/results/{res_id}", summary="删除测试结果")
def delete_result(res_id: str):
    """根据结果 ID 删除测试结果。"""
    return handle_call(lambda: service().delete_result(res_id))


@router.get("/results", summary="获取全部测试结果")
def get_all_result():
    """获取全部测试结果摘要。"""
    return handle_call(lambda: service().get_all_result())


@router.get("/results/names", summary="获取全部测试结果名称")
def get_all_result_name():
    """获取全部测试结果 ID 列表。"""
    return handle_call(lambda: service().get_all_result_name())


@router.get("/results/{res_id}", summary="读取测试结果")
def read_result(res_id: str):
    """根据结果 ID 读取测试结果详情。"""
    return handle_call(lambda: service().read_result(res_id))


@router.post("/results/read-batch", summary="批量读取测试结果")
def read_results(res_ids: list[str] = Body(..., embed=True)):
    """根据结果 ID 列表批量读取测试结果。"""
    return handle_call(lambda: service().read_results(res_ids))


# Run / Runner
@router.get("/runs", summary="获取运行记录")
def get_all_run(runner_id: str = ""):
    """根据 runner ID 获取运行记录。"""
    return handle_call(lambda: service().get_all_run(runner_id))


@router.post("/runners", summary="创建 Runner")
def create_runner(
    name: str = Body(...),
    endpoints: list[str] = Body(...),
    description: str = Body(""),
):
    """创建 runner，并绑定一组模型端点。"""
    return handle_call(lambda: service().create_runner(name, endpoints, description))


@router.delete("/runners/{runner_id}", summary="删除 Runner")
def delete_runner(runner_id: str):
    """根据 runner ID 删除 runner。"""
    return handle_call(lambda: service().delete_runner(runner_id))


@router.get("/runners", summary="获取全部 Runner")
def get_all_runner():
    """获取全部 runner 详情。"""
    return handle_call(lambda: service().get_all_runner())


@router.get("/runners/names", summary="获取全部 Runner 名称")
def get_all_runner_name():
    """获取全部 runner ID 列表。"""
    return handle_call(lambda: service().get_all_runner_name())


@router.get("/runners/{runner_id}/load", summary="加载 Runner")
def load_runner(runner_id: str):
    """根据 runner ID 加载 runner。"""
    return handle_call(lambda: service().load_runner(runner_id))


@router.get("/runners/{runner_id}", summary="读取 Runner")
def read_runner(runner_id: str):
    """根据 runner ID 读取 runner 配置。"""
    return handle_call(lambda: service().read_runner(runner_id))


# Session
@router.post("/sessions", summary="创建红队 Session")
def create_session(
    runner_id: str = Body(...),
    database_instance: Any = Body(...),
    endpoints: list[str] = Body(...),
    runner_args: dict[str, Any] = Body(...),
):
    """创建 red teaming session；通常建议后续封装成更高层业务接口。"""
    return handle_call(
        lambda: service().create_session(runner_id, database_instance, endpoints, runner_args)
    )


@router.post("/redteam/sessions", summary="Create Red Team Session")
def create_redteam_session(data: dict[str, Any] = Body(...)):
    """Create a runner-backed red-team session with endpoint and utility configuration."""
    return handle_call(
        lambda: service().create_redteam_session(
            name=data.get("name", ""),
            endpoints=data.get("endpoints", []),
            description=data.get("description", ""),
            runner_args=data.get("runner_args", {}),
        )
    )


@router.post("/redteam/prepare-prompt", summary="Prepare Red Team Prompt")
def prepare_redteam_prompt(data: dict[str, Any] = Body(...)):
    """Prepare the final prompt after applying Payload and Attack Module selections."""
    return handle_call(
        lambda: service().prepare_redteam_prompt(
            prompt=str(data.get("prompt", "")),
            prompt_template=str(data.get("prompt_template", "")),
            attack_module=str(data.get("attack_module", "")),
        )
    )


@router.post("/redteam/sessions/{runner_id}/prompt", summary="Send Red Team Prompt")
async def send_redteam_prompt(runner_id: str, data: dict[str, Any] = Body(...)):
    """Send one manual red-team prompt to a Moonshot session."""
    try:
        return await service().send_redteam_prompt(
            runner_id,
            str(data.get("user_prompt", "")),
            str(data.get("prepared_prompt", "")),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/sessions/{runner_id}", summary="删除红队 Session")
def delete_session(runner_id: str):
    """根据 runner ID 删除 red teaming session。"""
    return handle_call(lambda: service().delete_session(runner_id))


@router.get("/sessions/{runner_id}/chats", summary="获取 Session 聊天记录")
def get_all_chats_from_session(runner_id: str):
    """根据 runner ID 获取 session 聊天记录。"""
    return handle_call(lambda: service().get_all_chats_from_session(runner_id))


@router.get("/sessions/metadata", summary="获取全部 Session 元数据")
def get_all_session_metadata():
    """获取全部 red teaming session 元数据。"""
    return handle_call(lambda: service().get_all_session_metadata())


@router.get("/sessions/names", summary="获取全部 Session 名称")
def get_all_session_names():
    """获取全部 red teaming session 名称。"""
    return handle_call(lambda: service().get_all_session_names())


@router.get("/sessions/available", summary="获取可用 Session 信息")
def get_available_session_info():
    """获取可用 session ID 和元数据。"""
    return handle_call(lambda: service().get_available_session_info())


@router.get("/sessions/{runner_id}", summary="加载 Session")
def load_session(runner_id: str):
    """根据 runner ID 加载 session。"""
    return handle_call(lambda: service().load_session(runner_id))


@router.patch("/sessions/{runner_id}/attack-module", summary="更新 Session 攻击模块")
def update_attack_module(runner_id: str, attack_module_id: str = Body(..., embed=True)):
    """更新 session 使用的攻击模块。"""
    return handle_call(lambda: service().update_attack_module(runner_id, attack_module_id))


@router.patch("/sessions/{runner_id}/context-strategy", summary="更新 Session 上下文策略")
def update_context_strategy(runner_id: str, context_strategy: str = Body(..., embed=True)):
    """更新 session 使用的上下文策略。"""
    return handle_call(lambda: service().update_context_strategy(runner_id, context_strategy))


@router.patch("/sessions/{runner_id}/context-strategy/previous-prompts", summary="更新上下文历史轮数")
def update_cs_num_of_prev_prompts(
    runner_id: str,
    num_of_prev_prompts: int = Body(..., embed=True),
):
    """更新上下文策略使用的历史 prompt 数量。"""
    return handle_call(
        lambda: service().update_cs_num_of_prev_prompts(runner_id, num_of_prev_prompts)
    )


@router.patch("/sessions/{runner_id}/metric", summary="更新 Session 指标")
def update_metric(runner_id: str, metric_id: str = Body(..., embed=True)):
    """更新 session 使用的指标。"""
    return handle_call(lambda: service().update_metric(runner_id, metric_id))


@router.patch("/sessions/{runner_id}/prompt-template", summary="更新 Session Prompt 模板")
def update_prompt_template(runner_id: str, prompt_template: str = Body(..., embed=True)):
    """更新 session 使用的 Prompt 模板。"""
    return handle_call(lambda: service().update_prompt_template(runner_id, prompt_template))


@router.patch("/sessions/{runner_id}/system-prompt", summary="更新 Session 系统提示词")
def update_system_prompt(runner_id: str, system_prompt: str = Body(..., embed=True)):
    """更新 session 使用的系统提示词。"""
    return handle_call(lambda: service().update_system_prompt(runner_id, system_prompt))


# Bookmark
@router.get("/bookmarks", summary="获取全部书签")
def get_all_bookmarks():
    """获取全部 bookmark。"""
    return handle_call(lambda: service().get_all_bookmarks())


@router.get("/bookmarks/{bookmark_name}", summary="读取书签")
def get_bookmark(bookmark_name: str):
    """根据 bookmark 名称读取书签。"""
    return handle_call(lambda: service().get_bookmark(bookmark_name))


@router.post("/bookmarks", summary="新增书签")
def insert_bookmark(data: dict[str, Any] = Body(...)):
    """新增 red teaming bookmark。"""
    return handle_call(lambda: service().insert_bookmark(data))


@router.delete("/bookmarks/{bookmark_name}", summary="删除书签")
def delete_bookmark(bookmark_name: str):
    """根据 bookmark 名称删除书签。"""
    return handle_call(lambda: service().delete_bookmark(bookmark_name))


@router.delete("/bookmarks", summary="删除全部书签")
def delete_all_bookmark():
    """删除全部 bookmark。"""
    return handle_call(lambda: service().delete_all_bookmark())


@router.post("/bookmarks/export", summary="导出书签")
def export_bookmarks(export_file_name: str = Body("bookmarks", embed=True)):
    """导出 bookmark 文件。"""
    return handle_call(lambda: service().export_bookmarks(export_file_name))
