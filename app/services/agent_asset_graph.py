from __future__ import annotations

import re
from typing import Any


AGENT_ASSET_TYPES = {
    "actor",
    "entry_point",
    "input_data",
    "frontend",
    "backend",
    "agent_orchestrator",
    "prompt_instruction",
    "llm_model",
    "rag_retriever",
    "knowledge_base",
    "memory",
    "mcp_server",
    "tool_function",
    "external_system",
    "identity_permission",
    "security_control",
}

AGENT_ASSET_LAYERS = {
    "actor_entry",
    "application",
    "agent_core",
    "ai_knowledge",
    "action_integration",
    "security_governance",
}

AGENT_EDGE_TYPES = {
    "input_flow",
    "api_call",
    "prompt_flow",
    "retrieval",
    "tool_call",
    "data_access",
    "identity_binding",
    "control",
    "memory_read_write",
    "external_integration",
}

DEFAULT_LAYER_BY_TYPE = {
    "actor": "actor_entry",
    "entry_point": "actor_entry",
    "input_data": "actor_entry",
    "frontend": "application",
    "backend": "application",
    "agent_orchestrator": "agent_core",
    "prompt_instruction": "agent_core",
    "llm_model": "ai_knowledge",
    "rag_retriever": "ai_knowledge",
    "knowledge_base": "ai_knowledge",
    "memory": "ai_knowledge",
    "mcp_server": "action_integration",
    "tool_function": "action_integration",
    "external_system": "action_integration",
    "identity_permission": "security_governance",
    "security_control": "security_governance",
}

DEFAULT_NAME_BY_TYPE = {
    "actor": "Unknown Actor",
    "entry_point": "Unknown Entry Point",
    "input_data": "Unknown Input Data",
    "frontend": "Unknown Frontend",
    "backend": "Unknown Backend",
    "agent_orchestrator": "Unknown Agent Orchestrator",
    "prompt_instruction": "Unknown Prompt Instruction",
    "llm_model": "Unknown LLM Model",
    "rag_retriever": "Unknown RAG Retriever",
    "knowledge_base": "Unknown Knowledge Base",
    "memory": "Unknown Memory",
    "mcp_server": "Unknown MCP Server",
    "tool_function": "Unknown Tool Function",
    "external_system": "Unknown External System",
    "identity_permission": "Unknown Identity / Permission",
    "security_control": "Unknown Security Control",
}


def stable_id(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip().lower()).strip("-")
    return text or "asset"


def string_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []


def normalize_agent_asset_graph(raw: Any, project_name: str = "Agent Security Review") -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    seen: set[str] = set()
    assets: list[dict[str, Any]] = []
    for index, item in enumerate(source.get("assets") or [], start=1):
        if not isinstance(item, dict):
            continue
        asset_type = str(item.get("asset_type") or "")
        if asset_type not in AGENT_ASSET_TYPES:
            continue
        base_id = stable_id(item.get("id") or f"{asset_type}-{item.get('name') or index}")
        asset_id = base_id
        suffix = 2
        while asset_id in seen:
            asset_id = f"{base_id}-{suffix}"
            suffix += 1
        seen.add(asset_id)
        layer = str(item.get("layer") or DEFAULT_LAYER_BY_TYPE[asset_type])
        status = str(item.get("status") or "unknown")
        access_mode = str(item.get("access_mode") or "unknown")
        risk_hint = str(item.get("risk_hint") or "unknown")
        assets.append(
            {
                "id": asset_id,
                "name": str(item.get("name") or DEFAULT_NAME_BY_TYPE[asset_type]),
                "asset_type": asset_type,
                "layer": layer if layer in AGENT_ASSET_LAYERS else DEFAULT_LAYER_BY_TYPE[asset_type],
                "status": status if status in {"present", "inferred", "unknown"} else "unknown",
                "description": str(item.get("description") or ""),
                "owner": str(item.get("owner") or ""),
                "source_evidence": string_list(item.get("source_evidence")),
                "data_handled": string_list(item.get("data_handled")),
                "permissions": string_list(item.get("permissions")),
                "access_mode": access_mode if access_mode in {"read", "write", "read_write", "execute", "unknown"} else "unknown",
                "risk_hint": risk_hint if risk_hint in {"low", "medium", "high", "unknown"} else "unknown",
                "requires_approval": bool(item.get("requires_approval")),
                "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            }
        )

    present_types = {asset["asset_type"] for asset in assets}
    for asset_type in sorted(AGENT_ASSET_TYPES):
        if asset_type in present_types:
            continue
        asset_id = f"unknown-{asset_type}"
        seen.add(asset_id)
        assets.append(
            {
                "id": asset_id,
                "name": DEFAULT_NAME_BY_TYPE[asset_type],
                "asset_type": asset_type,
                "layer": DEFAULT_LAYER_BY_TYPE[asset_type],
                "status": "unknown",
                "description": "Not found in uploaded materials. Confirm whether this asset exists.",
                "source_evidence": [],
                "data_handled": [],
                "permissions": [],
                "access_mode": "unknown",
                "risk_hint": "unknown",
                "requires_approval": False,
                "metadata": {},
            }
        )

    asset_ids = {asset["id"] for asset in assets}
    relationships = []
    for index, item in enumerate(source.get("relationships") or [], start=1):
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("edge_type") or "")
        source_id = str(item.get("source") or "")
        target_id = str(item.get("target") or "")
        if edge_type not in AGENT_EDGE_TYPES or source_id not in asset_ids or target_id not in asset_ids or source_id == target_id:
            continue
        status = str(item.get("status") or "present")
        relationships.append(
            {
                "id": stable_id(item.get("id") or f"edge-{index}"),
                "source": source_id,
                "target": target_id,
                "edge_type": edge_type,
                "label": str(item.get("label") or ""),
                "description": str(item.get("description") or ""),
                "data_flow": string_list(item.get("data_flow")),
                "auth_context": str(item.get("auth_context") or ""),
                "status": status if status in {"present", "inferred", "unknown"} else "present",
            }
        )

    completeness = source.get("completeness") if isinstance(source.get("completeness"), dict) else {}
    questions = []
    for index, item in enumerate(completeness.get("missing_questions") or [], start=1):
        if not isinstance(item, dict):
            continue
        asset_type = str(item.get("asset_type") or "agent_orchestrator")
        impact = str(item.get("impact") or "medium")
        questions.append(
            {
                "id": str(item.get("id") or f"asset_mq_{index}"),
                "asset_type": asset_type if asset_type in AGENT_ASSET_TYPES else "agent_orchestrator",
                "question": str(item.get("question") or ""),
                "reason": str(item.get("reason") or ""),
                "impact": impact if impact in {"low", "medium", "high"} else "medium",
            }
        )
    missing_asset_types = [item for item in completeness.get("missing_asset_types") or [] if item in AGENT_ASSET_TYPES]
    score = float(completeness.get("score") or 0)
    if score <= 1:
        score *= 100
    status = str(completeness.get("status") or "insufficient")
    graph = {
        "version": str(source.get("version") or "1.0"),
        "graph_type": "agent_asset_flow",
        "project_name": str(source.get("project_name") or project_name),
        "summary": str(source.get("summary") or ""),
        "completeness": {
            "score": max(0, min(100, score)),
            "status": status if status in {"sufficient", "partial", "insufficient"} else "insufficient",
            "missing_asset_types": missing_asset_types,
            "missing_questions": questions,
        },
        "assets": assets,
        "relationships": relationships,
    }
    graph["relationships"] = enrich_architecture_relationships(graph["assets"], graph["relationships"])
    return graph


def first_asset(assets: list[dict[str, Any]], asset_type: str) -> dict[str, Any] | None:
    present = [asset for asset in assets if asset.get("asset_type") == asset_type and asset.get("status") != "unknown"]
    unknown = [asset for asset in assets if asset.get("asset_type") == asset_type]
    return (present or unknown or [None])[0]


def enrich_architecture_relationships(assets: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {(edge.get("source"), edge.get("target"), edge.get("edge_type")) for edge in relationships}

    def add(source: dict[str, Any] | None, target: dict[str, Any] | None, edge_type: str, label: str, status: str = "inferred") -> None:
        if not source or not target or source["id"] == target["id"]:
            return
        key = (source["id"], target["id"], edge_type)
        if key in existing:
            return
        existing.add(key)
        relationships.append(
            {
                "id": stable_id(f"arch-{source['id']}-{target['id']}-{edge_type}"),
                "source": source["id"],
                "target": target["id"],
                "edge_type": edge_type,
                "label": label,
                "description": "Architecture flow inferred from asset types when the model did not provide an explicit relationship.",
                "data_flow": [],
                "auth_context": "",
                "status": status,
            }
        )

    actor = first_asset(assets, "actor")
    entry = first_asset(assets, "entry_point")
    input_data = first_asset(assets, "input_data")
    frontend = first_asset(assets, "frontend")
    backend = first_asset(assets, "backend")
    agent = first_asset(assets, "agent_orchestrator")
    prompt = first_asset(assets, "prompt_instruction")
    llm = first_asset(assets, "llm_model")
    rag = first_asset(assets, "rag_retriever")
    kb = first_asset(assets, "knowledge_base")
    memory = first_asset(assets, "memory")
    mcp = first_asset(assets, "mcp_server")
    tool = first_asset(assets, "tool_function")
    external = first_asset(assets, "external_system")
    identity = first_asset(assets, "identity_permission")
    control = first_asset(assets, "security_control")

    add(actor, entry or input_data or frontend, "input_flow", "user input")
    add(entry, frontend or backend, "input_flow", "entry request")
    add(input_data, frontend or backend or agent, "input_flow", "input data")
    add(frontend, backend, "api_call", "API request")
    add(backend, agent, "api_call", "backend invokes agent")
    add(backend, tool, "tool_call", "function call")
    add(agent, prompt, "prompt_flow", "builds prompt")
    add(prompt, llm, "prompt_flow", "model call")
    add(agent, llm, "prompt_flow", "LLM reasoning")
    add(agent, rag, "retrieval", "retrieve context")
    add(rag, kb, "retrieval", "query knowledge")
    add(agent, memory, "memory_read_write", "read/write memory")
    add(agent, mcp, "tool_call", "MCP call")
    add(mcp, tool, "tool_call", "exposes tools")
    add(agent, tool, "tool_call", "tool call")
    add(tool, external, "external_integration", "external action")
    add(backend or agent, external, "external_integration", "integration")
    add(identity, backend or agent or tool, "identity_binding", "auth context")
    add(control, backend or agent or tool, "control", "security control")
    return relationships


def legacy_review_to_agent_asset_graph(review: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    assets: list[dict[str, Any]] = [
        {
            "id": "reviewer",
            "name": "Reviewer / User",
            "asset_type": "actor",
            "layer": "actor_entry",
            "status": "present",
            "description": "User providing prompts, materials, and supplemental answers.",
        },
        {
            "id": "agent-orchestrator",
            "name": project.get("projectName") or "Agent Orchestrator",
            "asset_type": "agent_orchestrator",
            "layer": "agent_core",
            "status": "inferred",
            "description": review.get("summary") or "Agent core inferred from the review project.",
        },
    ]
    relationships = [{"id": "rel-reviewer-agent", "source": "reviewer", "target": "agent-orchestrator", "edge_type": "input_flow", "label": "Provides input"}]
    for dimension in review.get("coverage_matrix") or []:
        for asset in dimension.get("detected_assets") or []:
            mapped_type = map_legacy_asset_type(str(asset.get("asset_type") or ""), str(dimension.get("dimension_id") or ""))
            asset_id = stable_id(asset.get("asset_id") or asset.get("name"))
            assets.append(
                {
                    "id": asset_id,
                    "name": asset.get("name") or asset_id,
                    "asset_type": mapped_type,
                    "layer": DEFAULT_LAYER_BY_TYPE[mapped_type],
                    "status": "present" if dimension.get("status") == "present" else "inferred",
                    "description": asset.get("description") or dimension.get("summary") or "",
                    "source_evidence": [item.get("excerpt") for item in dimension.get("evidence") or [] if isinstance(item, dict) and item.get("excerpt")],
                    "risk_hint": "high" if asset.get("risk_level") in {"high", "critical"} else "unknown",
                    "metadata": {"source_dimension_id": dimension.get("dimension_id")},
                }
            )
            relationships.append(
                {
                    "id": f"rel-{asset_id}-agent",
                    "source": asset_id,
                    "target": "agent-orchestrator",
                    "edge_type": edge_type_for_asset(mapped_type),
                    "label": "Informs agent flow",
                    "status": "inferred",
                }
            )
    missing_questions = [
        {
            "id": item.get("id"),
            "asset_type": map_dimension_to_asset_type(str(item.get("dimension_id") or "")),
            "question": item.get("question") or "",
            "reason": item.get("reason") or "",
            "impact": "high" if item.get("priority") in {"critical", "high"} else "medium",
        }
        for item in review.get("missing_questions") or []
    ]
    return normalize_agent_asset_graph(
        {
            "version": "1.0",
            "graph_type": "agent_asset_flow",
            "project_name": project.get("projectName") or "",
            "summary": review.get("summary") or "",
            "completeness": {
                "score": review.get("overall_confidence") or review.get("confidence") or 0,
                "status": "partial" if missing_questions else "sufficient",
                "missing_questions": missing_questions,
            },
            "assets": assets,
            "relationships": relationships,
        },
        project.get("projectName") or "",
    )


def map_dimension_to_asset_type(dimension_id: str) -> str:
    return {
        "D02": "identity_permission",
        "D03": "entry_point",
        "D04": "prompt_instruction",
        "D05": "llm_model",
        "D06": "tool_function",
        "D07": "rag_retriever",
        "D08": "external_system",
        "D09": "input_data",
        "D10": "backend",
        "D11": "memory",
        "D12": "security_control",
    }.get(dimension_id, "agent_orchestrator")


def map_legacy_asset_type(asset_type: str, dimension_id: str) -> str:
    aliases = {
        "agent_profile": "agent_orchestrator",
        "uploaded_material": "input_data",
        "uploaded_file": "input_data",
        "system_prompt": "prompt_instruction",
        "tool_spec": "tool_function",
        "rag_source": "knowledge_base",
        "api_endpoint": "entry_point",
        "identity": "identity_permission",
        "asset_dimension": map_dimension_to_asset_type(dimension_id),
    }
    return aliases.get(asset_type, map_dimension_to_asset_type(dimension_id))


def edge_type_for_asset(asset_type: str) -> str:
    return {
        "identity_permission": "identity_binding",
        "security_control": "control",
        "tool_function": "tool_call",
        "rag_retriever": "retrieval",
        "knowledge_base": "retrieval",
        "memory": "memory_read_write",
        "external_system": "external_integration",
        "backend": "api_call",
    }.get(asset_type, "input_flow")
