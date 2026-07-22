import base64
import json
import re
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.services.agent_asset_graph import legacy_review_to_agent_asset_graph, normalize_agent_asset_graph
from app.services.agent_security_review_store import AgentSecurityReviewStore
from app.services.file_extraction import IMAGE_EXTENSIONS, extract_text, json_preview


GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ASSET_REVIEW_TIMEOUT_SECONDS = 45
ASSET_REVIEW_MAX_TOKENS = 4096
RISK_REVIEW_TIMEOUT_SECONDS = 150
OPENAI_COMPATIBLE_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "kimi": "https://api.moonshot.cn/v1/chat/completions",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
}
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"


ASSET_DIMENSIONS = [
    ("D01", "Agent Profile", "Agent Profile", "Agent type, business goals, deployment environment, owner, business criticality, and lifecycle status."),
    ("D02", "Identity, Roles & Permission Boundary", "Identity, Roles & Permission Boundary", "User identity, agent identity, service accounts, token scope, delegated identity, tenant boundary, and privilege context."),
    ("D03", "Input Surfaces", "Input Surfaces", "Chat, file upload, API input, webhook, scheduled task, URL, email, form, voice, and every surface that can influence the agent."),
    ("D04", "Instruction & Prompt System", "Instruction & Prompt System", "System prompt, developer prompt, prompt templates, tool-use rules, refusal rules, strategy rules, and user-controlled variables."),
    ("D05", "Model, Runtime & Dependency Configuration", "Model, Runtime & Dependency Configuration", "Model provider/name/version, inference parameters, fallback models, runtime framework, SDKs, packages, container image, and deployment runtime."),
    ("D06", "Tools, Actions & Function Calls", "Tools, Actions & Function Calls", "Tool list, function parameters, call permissions, read/write/delete capability, external side effects, user confirmation, and audit logs."),
    ("D07", "Knowledge Base & RAG Pipeline", "Knowledge Base & RAG Pipeline", "Knowledge sources, document ingestion, vector database, embeddings, retriever, reranker, permission filtering, citations, and RAG cleaning."),
    ("D08", "External Systems, Connectors & Agent Protocols", "External Systems, Connectors & Agent Protocols", "Jira, Outlook, databases, CRM, MCP servers/tools, A2A, plugins, connectors, REST, GraphQL, WebSocket, and SSE."),
    ("D09", "Data Assets, Secrets & Sensitive Information", "Data Assets, Secrets & Sensitive Information", "User data, business data, PII, customer data, logs, tool results, tokens, API keys, secrets, credentials, and data classification."),
    ("D10", "Data Flow, Storage & Trust Boundaries", "Data Flow, Storage & Trust Boundaries", "Data sources, processing nodes, storage, logs, cache, encryption, retention, cross-tenant/region flow, third-party sharing, and trust boundaries."),
    ("D11", "Orchestration, Memory & State", "Orchestration, Memory & State", "Agent workflow, planner, memory, short-term context, long-term memory, state store, context reset, session boundary, and human approval."),
    ("D12", "Security Controls, Audit & Runtime Monitoring", "Security Controls, Audit & Runtime Monitoring", "Input/output filtering, tool-call policy, permission validation, audit logs, runtime monitoring, anomaly alerts, red team, evals, and incident response."),
]


ASSET_DIMENSION_PROMPT = "\n".join(
    f"- {dimension_id} {name} ({zh_name}): {description}"
    for dimension_id, name, zh_name, description in ASSET_DIMENSIONS
)

AGENT_ASSET_GRAPH_PROMPT = """
You are not a drawing tool. Do not output Mermaid, HTML, CSS, Vue code, or Vue Flow node style data.
Return only an AgentAssetGraph JSON object under the key "agentAssetGraph". AI controls facts only; the frontend controls layout and styles.
Allowed asset_type values only: actor, entry_point, input_data, frontend, backend, agent_orchestrator, prompt_instruction, llm_model, rag_retriever, knowledge_base, memory, mcp_server, tool_function, external_system, identity_permission, security_control.
Allowed layer values only: actor_entry, application, agent_core, ai_knowledge, action_integration, security_governance.
Allowed edge_type values only: input_flow, api_call, prompt_flow, retrieval, tool_call, data_access, identity_binding, control, memory_read_write, external_integration.
AgentAssetGraph shape:
{
  "version": "1.0",
  "graph_type": "agent_asset_flow",
  "project_name": "string",
  "summary": "string",
  "completeness": {
    "score": 0-100,
    "status": "sufficient|partial|insufficient",
    "missing_asset_types": ["asset_type"],
    "missing_questions": [{"id": "string", "asset_type": "asset_type", "question": "string", "reason": "string", "impact": "low|medium|high"}]
  },
  "assets": [
    {
      "id": "stable-reusable-id",
      "name": "short name",
      "asset_type": "allowed asset_type",
      "layer": "allowed layer",
      "status": "present|inferred|unknown",
      "description": "string",
      "owner": "string",
      "source_evidence": ["file or excerpt"],
      "data_handled": ["data"],
      "permissions": ["permission"],
      "access_mode": "read|write|read_write|execute|unknown",
      "risk_hint": "low|medium|high|unknown",
      "requires_approval": false,
      "metadata": {}
    }
  ],
  "relationships": [
    {
      "id": "stable-edge-id",
      "source": "asset id",
      "target": "asset id",
      "edge_type": "allowed edge_type",
      "label": "short label",
      "description": "string",
      "data_flow": ["data"],
      "auth_context": "string",
      "status": "present|inferred|unknown"
    }
  ]
}
Rules:
- Extract present assets from evidence first.
- Use inferred only when context strongly implies the asset.
- Add unknown assets for important AI Agent assets not found in materials; do not omit them.
- Generate missing_questions for missing facts.
- Relationship source and target must reference assets in the same graph.
- Do not invent custom asset_type or edge_type values.
Workflow graph requirements:
- This is not a D1-D12 inventory, not a swimlane diagram, and not a layered architecture wall. It must read like an AI Agent execution flow.
- The main horizontal path should be: actor/entry trigger -> application/backend -> AI Agent / agent_orchestrator -> router/control decision when present -> tool_function or external_system -> output/action.
- Model, memory, RAG retriever, knowledge base, identity, and policy/control nodes are supporting dependencies. Connect them to the Agent, backend, or tool, but do not make them dominate the main path.
- Prefer one central agent_orchestrator node named like the actual agent. If the evidence is weak, name it "AI Agent" and mark it inferred.
- Use prompt_instruction, llm_model, memory, rag_retriever, knowledge_base, identity_permission, and security_control as dependency nodes connected with prompt_flow, retrieval, memory_read_write, identity_binding, or control edges.
- If the agent uses function calling, represent agent_orchestrator -> tool_function with edge_type "tool_call" and a short action label.
- If tools call external SaaS, databases, email, Jira, file systems, cloud services, or internal APIs, represent tool_function -> external_system with edge_type "external_integration" or "data_access".
- Prefer 6-16 high-signal nodes over dozens of small inventory nodes. Avoid adding unknown nodes unless they are necessary for agent workflow understanding.
- Prefer concrete component names from evidence. Avoid vague names like "System", "Platform", or "Service" unless the evidence is truly vague.
"""


class GeminiService:
    def __init__(self, store: AgentSecurityReviewStore | None = None) -> None:
        self.store = store or AgentSecurityReviewStore()
        self.last_model_used = GEMINI_MODEL

    def test_connection(self, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        provider, model = self.resolve_model(settings)
        api_key = self.store.get_provider_api_key(provider)
        if not api_key:
            raise RuntimeError(f"{provider} API Key is not configured")
        text = self.request_model("Explain how AI works in a few words", [], provider, model, api_key, json_mode=False, max_tokens=256, timeout=30)
        return {"ok": bool(text), "provider": provider, "modelId": self.last_model_used}

    def run_material_question_review(self, project: dict[str, Any], project_dir: Path, job_id: str | None = None) -> dict[str, Any]:
        self.ensure_not_cancelled(project, job_id)
        materials, images = self.collect_material_inputs(project, project_dir)
        prompt = f"""
You are performing step 1 of an AI Agent Security Review.
Only review the uploaded development materials and manual inputs, then identify missing information the user must answer before any graph, capability inventory, or risk map is generated.
Do not generate AgentAssetGraph.
Do not generate Vue Flow.
Do not generate Mermaid, HTML, CSS, or Vue code.
Return JSON only with this shape:
{{
  "review_stage": "material_question_review",
  "schema_version": "2.1",
  "projectId": "string",
  "projectName": "string",
  "summary": "what is already understood from the materials",
  "confidence": 0.6,
  "overall_confidence": 0.6,
  "project_summary": {{"agent_type": "string", "review_status": "questions_required"}},
  "coverage_matrix": [],
  "features": [],
  "relationships": [],
  "components": [],
  "capabilities": [],
  "dataFlows": [],
  "assumptions": [],
  "missing_questions": []
}}
coverage_matrix MUST include exactly these 12 dimensions:
{ASSET_DIMENSION_PROMPT}
For each dimension, fill status, coverage_score, confidence, summary, detected_assets, missing_fields, evidence, related_capability_ids, related_graph_node_ids, unanswered_question_count, potential_risk_hints.
Generate concrete missing_questions for all material gaps required to build a clear AI Agent execution workflow graph:
- trigger actors and entry points
- frontend/backend handoff into the agent
- central agent runtime, planner, prompt registry, and tool router
- model, memory, RAG, and knowledge dependencies attached to the agent
- tool calls, write actions, MCP servers, and external action systems
- identity, tokens, permissions, service accounts used by the agent and tools
- controls, approvals, logs, and guardrails that affect the workflow
Every missing question must include id, dimension_id, related_capability_ids, related_asset_ids, priority, question, reason, answer_type, options, answer, blocks_risk_mapping.
Ask only useful questions. If the materials are complete, return an empty missing_questions array.

Project:
{json_preview(project)}

Extracted materials:
{materials}
"""
        settings = self.store.get_model_settings(project.get("projectId"))
        try:
            result = self.generate_json(
                prompt,
                expected_keys=["projectId", "coverage_matrix", "missing_questions"],
                images=images,
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=True,
            )
        except Exception as error:  # noqa: BLE001
            self.ensure_not_cancelled(project, job_id)
            if not self.should_fallback_asset_review(error):
                raise
            result = self.build_fallback_asset_review(project, materials, reason=str(error))
            result.pop("agentAssetGraph", None)
            result["features"] = []
            result["vueFlow"] = {"nodes": [], "edges": []}
        self.ensure_not_cancelled(project, job_id)
        result["features"] = []
        result["relationships"] = []
        result["asset_graph_nodes"] = []
        result["asset_graph_edges"] = []
        result["vueFlow"] = {"nodes": [], "edges": []}
        result.pop("agentAssetGraph", None)
        return self.normalize_function_review(result, project)

    def run_function_review(self, project: dict[str, Any], project_dir: Path, job_id: str | None = None) -> dict[str, Any]:
        self.ensure_not_cancelled(project, job_id)
        materials, images = self.collect_material_inputs(project, project_dir)
        prompt = f"""
You are an AI Agent system analysis assistant. Based on the uploaded design materials, perform an Asset Review for the AI Agent and produce a standardized AgentAssetGraph.
Do not analyze security risks. Do not output vulnerabilities, attacks, exploits, or risk recommendations.
Do not jump directly to risk mapping. The Asset Review is the gate before function map and risk map.
Do not merge everything into broad labels such as "chatbot" or "Q&A". Split into concrete executable capabilities for compatibility, but the primary graph output must be agentAssetGraph.
{AGENT_ASSET_GRAPH_PROMPT}
Return JSON only. The JSON must match this shape:
{{
  "review_stage": "asset_review",
  "schema_version": "2.0",
  "projectId": "string",
  "projectName": "string",
  "overall_confidence": 0.85,
  "project_summary": {{"agent_type": "string", "review_status": "asset_review_completed"}},
  "summary": "string",
  "confidence": 0.85,
  "coverage_matrix": [
    {{
      "dimension_id": "D01",
      "dimension_name": "Agent Profile",
      "dimension_zh_name": "Agent Profile",
      "status": "present",
      "coverage_score": 0.85,
      "confidence": 0.85,
      "summary": "short coverage summary",
      "detected_assets": [
        {{
          "asset_id": "asset_D01_1",
          "asset_type": "agent_profile",
          "name": "Production RAG Agent",
          "description": "What was identified.",
          "properties": {{}},
          "source_dimension_id": "D01",
          "confidence": 0.85,
          "risk_level": "none"
        }}
      ],
      "missing_fields": ["field"],
      "evidence": [
        {{"evidence_id": "ev_1", "source_type": "uploaded_file", "source_name": "architecture.pdf", "excerpt": "short source excerpt", "confidence": 0.8}}
      ],
      "related_capability_ids": ["F001"],
      "related_graph_node_ids": ["F001"],
      "potential_risk_hints": ["hint only, not a formal risk finding"],
      "unanswered_question_count": 0
    }}
  ],
  "features": [
    {{
      "id": "F001",
      "name": "Concrete feature name",
      "mapped_dimensions": ["D03", "D11"],
      "related_asset_ids": ["asset_D03_1"],
      "status": "present",
      "description": "What this feature does.",
      "trigger": "How this feature is triggered.",
      "inputs": ["user text", "uploaded image", "project id"],
      "outputs": ["natural language answer", "structured JSON", "ticket id"],
      "components": ["Agent Runtime", "LLM", "Tool Router"],
      "tools": [
        {{
          "name": "tool_or_connector_name",
          "operation": "read/write",
          "externalSystem": "system name",
          "inputParameters": ["parameter"],
          "returns": ["result"]
        }}
      ],
      "rag": {{"used": false, "knowledge_sources": [], "retrieval_conditions": [], "returns_citations": false}},
      "file_or_image_processing": {{"used": false, "types": [], "flow": "how files/images are processed"}},
      "external_systems": ["system"],
      "data_assets": ["data asset"],
      "permissions": ["permission"],
      "dependencies": ["dependency"],
      "evidence": ["source"],
      "missing_fields": ["field"],
      "flow_next": ["F002"]
    }}
  ],
  "relationships": [{{"id": "rel_1", "source": "F001", "target": "F002", "type": "flow", "label": "Next step"}}],
  "asset_graph_nodes": [{{"id": "asset_D02_1", "label": "Service Account", "type": "identity", "dimension_id": "D02", "asset_id": "asset_D02_1"}}],
  "asset_graph_edges": [{{"id": "asset_edge_1", "source": "asset_D02_1", "target": "F003", "type": "used_by", "label": "Used by capability"}}],
  "components": [{{"id": "frontend", "name": "Frontend", "type": "frontend", "description": "string", "sourceFiles": [], "properties": {{}}}}],
  "capabilities": [{{"id": "capability_search_docs", "name": "Search documents", "type": "read", "description": "string", "relatedComponents": []}}],
  "dataFlows": [{{"id": "flow_user_to_agent", "source": "user", "target": "agent_runtime", "label": "User message", "description": "string", "dataType": "prompt"}}],
  "assumptions": [{{"id": "assumption_1", "text": "string", "confidence": 0.7}}],
  "missingInformation": [{{"id": "missing_1", "question": "string", "reason": "string"}}],
  "missing_questions": [
    {{
      "id": "mq_D06_1",
      "dimension_id": "D06",
      "related_capability_ids": ["F003"],
      "related_asset_ids": ["asset_D06_1"],
      "priority": "critical",
      "question": "Is the Jira tool read-only or write-capable?",
      "reason": "Tool write access changes risk map readiness.",
      "answer_type": "text",
      "options": [],
      "answer": "",
      "blocks_risk_mapping": true
    }}
  ],
  "agentAssetGraph": {{"version": "1.0", "graph_type": "agent_asset_flow", "project_name": "string", "summary": "string", "completeness": {{"score": 0, "status": "partial", "missing_asset_types": [], "missing_questions": []}}, "assets": [], "relationships": []}},
  "vueFlow": {{"nodes": [], "edges": []}}
}}
Asset dimensions are fixed. coverage_matrix MUST include exactly these 12 dimensions even when a dimension is not found or not applicable:
{ASSET_DIMENSION_PROMPT}
Use coverage status values only: present, partial, missing, unknown, not_applicable, high_risk.
If a critical missing question blocks risk mapping, set blocks_risk_mapping to true.
Collect detected_assets professionally, not just broad features. Pay special attention to:
- D02 fields: user_types, user_roles, permission_model, tenant_boundary, agent_identity, service_account, delegated_user_identity, token_storage, token_scope, privilege_level, cross_tenant_access, impersonation_supported, identity_propagation_to_tools, admin_capabilities.
- D05 fields: model_provider, model_name, model_version, deployment_mode, inference_parameters, safety_settings, fallback_models, runtime_framework, agent_framework, sdk_dependencies, package_dependencies, container_image, environment_variables, prompt_template_source, dependency_update_policy.
- D08 fields: external_systems, api_endpoints, protocol_type, connector_type, mcp_servers, mcp_tools, a2a_agents, plugins, browser_automation, workflow_automation, websocket_channels, sse_streams, local_file_access, code_interpreter_access, connector_auth_method, connector_permission_scope.
- D09 fields: pii_data, business_data, customer_data, internal_data, regulated_data, uploaded_files, conversation_history, tool_results, rag_context, api_keys, access_tokens, refresh_tokens, credentials, secrets, secret_storage, secret_rotation, data_classification.
- D10 fields: data_sources, data_processors, data_destinations, storage_locations, log_locations, cache_locations, encryption_at_rest, encryption_in_transit, retention_policy, cross_region_transfer, cross_tenant_flow, third_party_sharing, trust_boundaries, user_to_agent_boundary, agent_to_tool_boundary, agent_to_rag_boundary, agent_to_external_system_boundary.
- D11 fields: orchestrator, workflow_steps, planner_enabled, tool_selection_logic, retry_logic, human_approval, short_term_memory, long_term_memory, memory_write_policy, memory_read_scope, memory_sanitization, memory_isolation, state_store, session_boundary, context_reset, conversation_retention, multi_agent_coordination.
Do not populate Vue Flow styles or positions. If vueFlow is included for backward compatibility, keep it empty; agentAssetGraph is the source of truth for rendering.
Flow quality rules:
- The features array is the source of truth for the rendered flow map. Use stable feature ids F001, F002, F003... and make every important workflow step a capability.
- Every feature must map to one or more asset dimensions in mapped_dimensions.
- Use flow_next to express the real business sequence between features. Do not create unrelated loops.
- Prefer a left-to-right workflow: ingestion/input steps -> parsing/indexing/retrieval -> agent/runtime decision -> tool/external system action -> result.
- Keep node names short, operational, and specific. Avoid vague titles such as "System" or "Platform".
- If a feature is triggered by a user prompt, say so in trigger. If it uses RAG, fill rag.used and knowledge_sources.
- If a feature calls external APIs/tools, include tools entries and set operation read/write accurately.
The Vue Flow graph may be sparse, but if populated its node ids should match feature ids or "user"; edge source/target must reference existing ids.

Project:
{json_preview(project)}

Extracted materials:
{materials}
"""
        settings = self.store.get_model_settings(project.get("projectId"))
        try:
            self.ensure_not_cancelled(project, job_id)
            result = self.generate_json(
                prompt,
                expected_keys=["projectId", "coverage_matrix", "features", "missing_questions", "agentAssetGraph"],
                images=images,
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=True,
            )
        except Exception as error:  # noqa: BLE001
            self.ensure_not_cancelled(project, job_id)
            if not self.should_fallback_asset_review(error):
                raise
            result = self.build_fallback_asset_review(project, materials, reason=str(error))
        self.ensure_not_cancelled(project, job_id)
        return self.normalize_function_review(result, project)

    def update_function_map(self, project: dict[str, Any], project_dir: Path, payload: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
        self.ensure_not_cancelled(project, job_id)
        mode = str(payload.get("mode") or "review_again")
        if mode == "review_again":
            gap_review = self.review_asset_gaps(project, payload)
            self.ensure_not_cancelled(project, job_id)
            if gap_review.get("coverage_complete") is False and gap_review.get("missing_questions"):
                current = project.get("functionReview") or {}
                merged = {
                    **current,
                    "projectId": project.get("projectId"),
                    "projectName": project.get("projectName", ""),
                    "summary": gap_review.get("summary") or "Additional supplemental information is required before generating the inventory.",
                    "confidence": gap_review.get("confidence", current.get("confidence", 0.35)),
                    "overall_confidence": gap_review.get("confidence", current.get("overall_confidence", 0.35)),
                    "coverage_matrix": gap_review.get("coverage_matrix") or current.get("coverage_matrix") or [],
                    "missing_questions": gap_review.get("missing_questions") or [],
                    "features": current.get("features") or [],
                    "relationships": current.get("relationships") or [],
                    "asset_graph_nodes": current.get("asset_graph_nodes") or [],
                    "asset_graph_edges": current.get("asset_graph_edges") or [],
                    "vueFlow": current.get("vueFlow") or project.get("functionMap") or {"nodes": [], "edges": []},
                }
                return self.normalize_function_review(merged, project)
        return self.run_progressive_asset_review(project, project_dir, payload, mode, job_id=job_id)

    def review_asset_gaps(self, project: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""
You are checking whether an AI Agent Asset Review has enough information across D01-D12.
Compare uploaded/manual materials, current missing-information answers, and the existing review against the fixed dimensions below.
Do not generate capabilities or maps in this step.
Return JSON only:
{{
  "coverage_complete": false,
  "summary": "short reason",
  "confidence": 0.7,
  "coverage_matrix": [],
  "missing_questions": []
}}
If coverage is comprehensive enough to generate a professional asset inventory, set coverage_complete=true and return an empty missing_questions array.
If not comprehensive, return only the new or still-unanswered high-value questions needed for D01-D12. Avoid repeating questions already answered in missingAnswers.
Each question must include id, dimension_id, related_capability_ids, related_asset_ids, priority, question, reason, answer_type, options, answer, blocks_risk_mapping.
Asset dimensions:
{ASSET_DIMENSION_PROMPT}

Current project and review:
{json_preview(project)}

User updates:
{json_preview(payload)}
"""
        settings = self.store.get_model_settings(project.get("projectId"))
        try:
            return self.generate_json(
                prompt,
                expected_keys=["coverage_complete", "summary", "missing_questions"],
                images=[],
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=False,
            )
        except Exception as error:  # noqa: BLE001
            if not self.should_fallback_asset_review(error):
                raise
            return {"coverage_complete": True, "summary": f"Gap check could not complete, continuing with generation. Detail: {error}", "confidence": 0.35, "missing_questions": []}

    def run_progressive_asset_review(self, project: dict[str, Any], project_dir: Path, payload: dict[str, Any], mode: str, job_id: str | None = None) -> dict[str, Any]:
        materials, images = self.collect_material_inputs(project, project_dir)
        settings = self.store.get_model_settings(project.get("projectId"))
        direct_instruction = (
            "Generate even if some fields are incomplete. Do not block output with new missing questions; capture uncertainty in missing_fields and assumptions."
            if mode == "direct"
            else "Generate because the supplemental answers are sufficient. Only include non-blocking missing questions for minor residual unknowns."
        )
        try:
            self.ensure_not_cancelled(project, job_id)
            self.store.update_project(project["projectId"], {"status": "asset_review_assets_running"})
            asset_result = self.generate_json(
                self.asset_inventory_prompt(project, payload, materials, direct_instruction),
                expected_keys=["projectId", "coverage_matrix", "summary"],
                images=images,
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=False,
            )
            self.ensure_not_cancelled(project, job_id)
            asset_review = self.normalize_function_review({**asset_result, "features": [], "missing_questions": asset_result.get("missing_questions") or [], "vueFlow": {"nodes": [], "edges": []}}, project)

            self.store.update_project(project["projectId"], {"status": "asset_review_capabilities_running"})
            capability_result = self.generate_json(
                self.capability_inventory_prompt(project, payload, asset_review, direct_instruction),
                expected_keys=["projectId", "features", "relationships"],
                images=[],
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=False,
            )
            self.ensure_not_cancelled(project, job_id)

            merged_for_graph = self.normalize_function_review({**asset_review, **capability_result, "coverage_matrix": asset_review["coverage_matrix"]}, project)
            self.store.update_project(project["projectId"], {"status": "asset_review_graph_running"})
            graph_result = self.generate_json(
                self.asset_flow_graph_prompt(project, payload, merged_for_graph, direct_instruction),
                expected_keys=["projectId", "agentAssetGraph"],
                images=[],
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=True,
            )
            self.ensure_not_cancelled(project, job_id)
            final = {
                **merged_for_graph,
                "summary": graph_result.get("summary") or merged_for_graph.get("summary") or "",
                "agentAssetGraph": graph_result.get("agentAssetGraph") or merged_for_graph.get("agentAssetGraph"),
                "asset_graph_nodes": graph_result.get("asset_graph_nodes") or merged_for_graph.get("asset_graph_nodes") or [],
                "asset_graph_edges": graph_result.get("asset_graph_edges") or merged_for_graph.get("asset_graph_edges") or [],
                "vueFlow": merged_for_graph.get("vueFlow") or {"nodes": [], "edges": []},
                "relationships": graph_result.get("relationships") or merged_for_graph.get("relationships") or [],
            }
            return self.normalize_function_review(final, project)
        except Exception as error:  # noqa: BLE001
            self.ensure_not_cancelled(project, job_id)
            if not self.should_fallback_asset_review(error):
                raise
            result = self.build_fallback_asset_review(project, materials, reason=str(error))
            return self.normalize_function_review(result, project)

    def asset_inventory_prompt(self, project: dict[str, Any], payload: dict[str, Any], materials: str, instruction: str) -> str:
        return f"""
You are performing stage 1 of 3 for an AI Agent Security Review: AI Agent Asset Inventory.
{instruction}
Return JSON only with projectId, projectName, summary, confidence, overall_confidence, project_summary, coverage_matrix, assumptions, missing_questions.
coverage_matrix MUST include exactly the 12 fixed dimensions. For every dimension, identify concrete assets with asset_id, asset_type, name, description, properties, source_dimension_id, confidence, risk_level.
Make the inventory professional and specific; avoid broad placeholders unless the evidence truly lacks detail.
Asset dimensions:
{ASSET_DIMENSION_PROMPT}

Project:
{json_preview(project)}

User updates:
{json_preview(payload)}

Extracted materials:
{materials}
"""

    def capability_inventory_prompt(self, project: dict[str, Any], payload: dict[str, Any], asset_review: dict[str, Any], instruction: str) -> str:
        return f"""
You are performing stage 2 of 3: Capability Inventory.
{instruction}
Use the confirmed asset inventory to extract concrete executable agent capabilities. Split workflows into operational capabilities, not broad labels.
Return JSON only with projectId, summary, features, relationships, components, capabilities, dataFlows.
Each feature must include id F001..., name, mapped_dimensions, related_asset_ids, status, description, trigger, inputs, outputs, components, tools, rag, file_or_image_processing, external_systems, data_assets, permissions, dependencies, evidence, missing_fields, flow_next.
Relationships should express the real sequence between features.

Asset inventory:
{json_preview(asset_review)}

Project and user updates:
{json_preview({"project": project, "payload": payload})}
"""

    def asset_flow_graph_prompt(self, project: dict[str, Any], payload: dict[str, Any], review: dict[str, Any], instruction: str) -> str:
        return f"""
You are performing stage 3 of 3: Rich AI Agent Workflow Graph.
{instruction}
Build a standardized AgentAssetGraph that represents this specific agent as an execution workflow, similar to a professional node-based agent builder.
The graph must emphasize the main path: trigger/input -> application/backend -> AI Agent -> decision/router/control -> tool/external action/output.
Model, memory, prompt, RAG, knowledge base, identity, and guardrails should appear as supporting dependency nodes connected to the central agent/tool path.
{AGENT_ASSET_GRAPH_PROMPT}
Return JSON only with projectId, summary, agentAssetGraph. Do not return Mermaid, HTML, CSS, Vue, or Vue Flow style/position data.
Prefer 6-16 meaningful workflow nodes. Do not output a broad asset inventory wall. Add unknown nodes only when required to explain the workflow.

Current review:
{json_preview(review)}

Project and user updates:
{json_preview({"project": project, "payload": payload})}
"""

    def update_function_map_legacy(self, project: dict[str, Any], project_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""
You are an AI Agent system analysis assistant. Update the existing Asset Review, feature inventory, and function review map using user edits and answers.
Do not analyze security risks. Return the complete Function Review JSON only, preserving user-confirmed feature descriptions and map edits when possible.
The JSON must keep review_stage="asset_review", schema_version="2.0", a complete 12-item coverage_matrix, missing_questions, asset_graph_nodes, asset_graph_edges, and a "features" array with concrete feature id, name, mapped_dimensions, related_asset_ids, status, description, trigger, inputs, outputs, components, tools, rag, file_or_image_processing, evidence, missing_fields, and flow_next fields.
Asset dimensions are fixed and coverage_matrix MUST include exactly these 12 dimensions:
{ASSET_DIMENSION_PROMPT}
Use answered missing information to reduce unanswered_question_count, update missing_fields, and unblock risk mapping when critical answers are present.

Current project and review:
{json_preview(project)}

User updates:
{json_preview(payload)}
"""
        settings = self.store.get_model_settings(project.get("projectId"))
        try:
            result = self.generate_json(
                prompt,
                expected_keys=["projectId", "coverage_matrix", "features", "missing_questions", "vueFlow"],
                images=[],
                settings=settings,
                max_tokens=ASSET_REVIEW_MAX_TOKENS,
                timeout=ASSET_REVIEW_TIMEOUT_SECONDS,
                repair=False,
            )
        except Exception as error:  # noqa: BLE001
            if not self.should_fallback_asset_review(error):
                raise
            result = self.build_fallback_asset_review(project, json_preview(payload), reason=str(error))
        return self.normalize_function_review(result, project)

    def run_risk_review(self, project: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
        self.ensure_not_cancelled(project, job_id)
        prompt = f"""
You are an AI Agent security design audit assistant. Based only on the confirmed function review JSON, current Vue Flow function map, user edits, and missing-information answers, identify AI Agent design risks.
Generate a risk map based on the function map. Do not draw an unrelated graph.
Risk location rules:
- location.nodes must reference feature ids from the confirmed function review (for example "F001") or "user"; do not invent node ids.
- location.edges should reference real flow ids when available, but can be empty.
- If a risk spans multiple workflow steps, include all affected feature ids.
- The returned vueFlow should preserve the same feature ids and business order; avoid cycles unless the business workflow truly loops.
- The risk map is an overlay of the confirmed feature workflow, not a new architecture diagram.
Return JSON only with this shape:
{{
  "projectId": "string",
  "summary": "string",
  "risks": [
    {{
      "id": "R1",
      "title": "Direct Prompt Injection",
      "severity": "high",
      "category": "Prompt Injection",
      "location": {{"nodes": ["user"], "edges": []}},
      "description": "string",
      "impact": "string",
      "recommendation": "string"
    }}
  ],
  "vueFlow": {{"nodes": [], "edges": []}},
  "reportMarkdown": "string"
}}
Use severity values critical, high, medium, or low.

Confirmed function review context:
{json_preview(project)}
"""
        settings = self.store.get_model_settings(project.get("projectId"))
        result = self.generate_json(prompt, expected_keys=["projectId", "risks", "vueFlow", "reportMarkdown"], images=[], settings=settings, timeout=RISK_REVIEW_TIMEOUT_SECONDS)
        self.ensure_not_cancelled(project, job_id)
        return self.normalize_risk_review(result, project)

    def ensure_not_cancelled(self, project: dict[str, Any], job_id: str | None = None) -> None:
        project_id = str(project.get("projectId") or "")
        if project_id and self.store.is_review_cancelled(project_id, job_id):
            raise RuntimeError("Review cancelled by user.")

    def collect_material_inputs(self, project: dict[str, Any], project_dir: Path) -> tuple[str, list[dict[str, Any]]]:
        chunks: list[str] = []
        images: list[dict[str, Any]] = []
        for material in project.get("materials", []):
            file_path = project_dir / "materials" / material.get("storedName", "")
            if not file_path.exists():
                continue
            text, supported, note = extract_text(file_path)
            chunks.append(f"\n--- {material.get('fileName')} [{material.get('tag')}] ---")
            if text:
                chunks.append(text[:24000])
            elif note:
                chunks.append(note)
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(self.image_part(file_path))
            material["extractionSupported"] = supported or file_path.suffix.lower() in IMAGE_EXTENSIONS
            material["extractionNote"] = note
        manual = project.get("manualInputs") or {}
        chunks.append("\n--- Manual Inputs ---")
        chunks.append(json_preview(manual))
        return "\n".join(chunks)[:60000], images[:3]

    def build_fallback_asset_review(self, project: dict[str, Any], materials: str, reason: str) -> dict[str, Any]:
        project_id = str(project.get("projectId") or "")
        project_name = str(project.get("projectName") or "")
        uploaded_files = project.get("materials") or []
        manual = project.get("manualInputs") or {}
        has_manual = any(str(value or "").strip() for value in manual.values())
        has_files = bool(uploaded_files)
        evidence = [
            {
                "evidence_id": "ev_fallback_1",
                "source_type": "inferred",
                "source_name": "Fast fallback asset review",
                "excerpt": f"Model asset review timed out, so a conservative local asset inventory was generated. Timeout detail: {reason}",
                "confidence": 0.35,
            }
        ]
        if has_files:
            evidence.append(
                {
                    "evidence_id": "ev_uploads",
                    "source_type": "uploaded_file",
                    "source_name": ", ".join(str(item.get("fileName") or "uploaded file") for item in uploaded_files[:3]),
                    "excerpt": "Uploaded material exists and requires deeper AI review for visual/text details.",
                    "confidence": 0.45,
                }
            )
        if has_manual:
            evidence.append(
                {
                    "evidence_id": "ev_manual",
                    "source_type": "manual_input",
                    "source_name": "Manual Inputs",
                    "excerpt": "Manual inputs were provided and used for the fallback inventory.",
                    "confidence": 0.5,
                }
            )
        saved_answers = project.get("missingAnswers") or {}
        dimensions = []
        for dimension_id, name, zh_name, description in ASSET_DIMENSIONS:
            detected_assets: list[dict[str, Any]] = []
            missing_fields = self.fallback_missing_fields(dimension_id)
            status = "unknown"
            if dimension_id == "D01":
                detected_assets.append(self.fallback_asset(dimension_id, "agent_profile", project_name or "Agent Review Project", f"{project.get('agentType') or 'Agent'} under review."))
                status = "partial"
            elif dimension_id == "D03" and has_files:
                detected_assets.append(self.fallback_asset(dimension_id, "uploaded_material", "Material Upload", "Uploaded evidence is an input surface for this review."))
                status = "partial"
            elif dimension_id == "D04" and manual.get("systemPrompt"):
                detected_assets.append(self.fallback_asset(dimension_id, "system_prompt", "System Prompt", "Manual system prompt was provided."))
                status = "partial"
            elif dimension_id == "D06" and manual.get("toolList"):
                detected_assets.append(self.fallback_asset(dimension_id, "tool_spec", "Tool List", "Manual tool list was provided."))
                status = "partial"
            elif dimension_id == "D07" and manual.get("ragSource"):
                detected_assets.append(self.fallback_asset(dimension_id, "rag_source", "RAG Source", "Manual RAG source was provided."))
                status = "partial"
            elif dimension_id == "D08" and manual.get("apiEndpointDescription"):
                detected_assets.append(self.fallback_asset(dimension_id, "api_endpoint", "API / Endpoint Description", "Manual endpoint description was provided."))
                status = "partial"
            elif dimension_id == "D09" and has_files:
                detected_assets.append(self.fallback_asset(dimension_id, "uploaded_file", "Uploaded File", "Uploaded files may contain user, business, or sensitive data.", "unknown"))
                status = "partial"
            dimension_questions = self.fallback_questions_for_dimension(dimension_id)
            for question in dimension_questions:
                if question["id"] in saved_answers:
                    question["answer"] = saved_answers[question["id"]]
            dimensions.append(
                {
                    "dimension_id": dimension_id,
                    "dimension_name": name,
                    "dimension_zh_name": zh_name,
                    "status": status,
                    "coverage_score": 0.45 if detected_assets else 0.15,
                    "confidence": 0.45 if detected_assets else 0.2,
                    "summary": f"{description} Fast fallback inventory was used because the model timed out.",
                    "detected_assets": detected_assets,
                    "missing_fields": missing_fields,
                    "evidence": evidence,
                    "related_capability_ids": ["F001"] if dimension_id in {"D01", "D03", "D09", "D10"} else [],
                    "related_graph_node_ids": ["F001"] if dimension_id in {"D01", "D03", "D09", "D10"} else [],
                    "unanswered_question_count": sum(1 for question in dimension_questions if not question.get("answer")),
                    "potential_risk_hints": self.fallback_risk_hints(dimension_id),
                }
            )
        missing_questions = []
        for dimension_id, *_ in ASSET_DIMENSIONS:
            for question in self.fallback_questions_for_dimension(dimension_id):
                if question["id"] in saved_answers:
                    question["answer"] = saved_answers[question["id"]]
                missing_questions.append(question)
        review = {
            "review_stage": "asset_review",
            "schema_version": "2.0",
            "projectId": project_id,
            "projectName": project_name,
            "overall_confidence": 0.35,
            "project_summary": {
                "agent_type": project.get("agentType") or "",
                "review_status": "fallback_asset_review_completed",
                "fallback_reason": reason,
            },
            "summary": "Fast fallback asset inventory generated because the model asset review timed out. Answer the missing questions or retry Asset Review for a deeper AI pass.",
            "confidence": 0.35,
            "coverage_matrix": dimensions,
            "features": [
                {
                    "id": "F001",
                    "name": "Initial Agent Interaction",
                    "mapped_dimensions": ["D01", "D03", "D09", "D10"],
                    "related_asset_ids": ["asset_D01_1"],
                    "status": "inferred",
                    "description": "Initial inferred capability based on the created review project and uploaded materials.",
                    "trigger": "User input or uploaded design material.",
                    "inputs": ["uploaded materials", "manual inputs"],
                    "outputs": ["asset review context"],
                    "components": ["Agent Review Workspace"],
                    "tools": [],
                    "rag": {"used": bool(manual.get("ragSource")), "knowledge_sources": [], "retrieval_conditions": [], "returns_citations": False},
                    "file_or_image_processing": {"used": has_files, "types": [str(item.get("extension") or "file") for item in uploaded_files], "flow": "Uploaded files are collected as review evidence."},
                    "external_systems": [],
                    "data_assets": ["uploaded files"] if has_files else [],
                    "permissions": [],
                    "dependencies": [],
                    "evidence": ["fallback asset review"],
                    "missing_fields": ["confirmed workflow", "confirmed tools", "confirmed data flow"],
                    "flow_next": [],
                }
            ],
            "relationships": [{"id": "rel_fallback_user_f001", "source": "user", "target": "F001", "type": "input", "label": "Provides review evidence"}],
            "asset_graph_nodes": [
                {
                    "id": f"dimension_{dimension_id}",
                    "label": name,
                    "type": "asset_dimension",
                    "dimension_id": dimension_id,
                    "asset_id": f"dimension_{dimension_id}",
                    "description": description,
                }
                for dimension_id, name, _, description in ASSET_DIMENSIONS
            ],
            "asset_graph_edges": [
                {
                    "id": f"asset_edge_{dimension_id}_F001",
                    "source": f"dimension_{dimension_id}",
                    "target": "F001",
                    "type": "review_scope",
                    "label": "Informs review",
                }
                for dimension_id, *_ in ASSET_DIMENSIONS
            ],
            "components": [],
            "capabilities": [],
            "dataFlows": [],
            "assumptions": [{"id": "assumption_fallback_1", "text": "Fallback inventory is conservative and should be updated with user answers.", "confidence": 0.35}],
            "missingInformation": [],
            "missing_questions": missing_questions,
            "vueFlow": {
                "nodes": [
                    {"id": "user", "type": "custom", "position": {"x": 0, "y": 0}, "data": {"label": "User / Reviewer", "nodeType": "User", "description": "Provides design evidence."}},
                    {"id": "F001", "type": "custom", "position": {"x": 280, "y": 0}, "data": {"label": "Initial Agent Interaction", "nodeType": "Feature", "description": "Fallback inferred capability.", "featureId": "F001"}},
                ],
                "edges": [{"id": "flow-user-F001", "source": "user", "target": "F001", "label": "Review evidence", "data": {"flowType": "Input"}}],
            },
        }
        review["agentAssetGraph"] = legacy_review_to_agent_asset_graph(review, project)
        return review

    def fallback_asset(self, dimension_id: str, asset_type: str, name: str, description: str, risk_level: str = "unknown") -> dict[str, Any]:
        return {
            "asset_id": f"asset_{dimension_id}_1",
            "asset_type": asset_type,
            "name": name,
            "description": description,
            "properties": {},
            "source_dimension_id": dimension_id,
            "confidence": 0.45,
            "risk_level": risk_level,
        }

    def fallback_missing_fields(self, dimension_id: str) -> list[str]:
        fields = {
            "D02": ["agent_identity", "service_account", "token_scope", "delegated_user_identity", "tenant_boundary"],
            "D05": ["model_provider", "model_version", "runtime_framework", "sdk_dependencies", "dependency_update_policy"],
            "D06": ["tool_permissions", "write_actions", "user_confirmation", "audit_logs"],
            "D07": ["knowledge_sources", "permission_filtering", "rag_ingestion_cleaning"],
            "D08": ["connector_type", "protocol_type", "mcp_servers", "a2a_agents", "connector_auth_method"],
            "D09": ["pii_data", "api_keys", "access_tokens", "secret_storage", "data_classification"],
            "D10": ["storage_locations", "retention_policy", "trust_boundaries", "third_party_sharing"],
            "D11": ["short_term_memory", "long_term_memory", "memory_isolation", "session_boundary"],
            "D12": ["input_filtering", "output_filtering", "runtime_monitoring", "incident_response"],
        }
        return fields.get(dimension_id, ["confirmed details"])

    def fallback_questions_for_dimension(self, dimension_id: str) -> list[dict[str, Any]]:
        question_map = {
            "D02": [
                ("mq_D02_identity", "critical", "Does the Agent have its own identity, or does it only act on behalf of users?", "Identity model is required before permission and risk mapping.", True),
                ("mq_D02_service_account", "critical", "When calling tools, does the Agent use a service account or delegated user identity?", "Tool authorization context determines privilege boundaries.", True),
                ("mq_D02_token_scope", "high", "Where are tokens stored and what scopes do they have?", "Token storage and scope affect credential exposure.", False),
            ],
            "D05": [
                ("mq_D05_model_runtime", "high", "Which model provider, model version, runtime framework, and SDK dependencies are used?", "Supply-chain and runtime dependency context is incomplete.", False),
            ],
            "D06": [
                ("mq_D06_tool_write", "critical", "Which tools can write, delete, or trigger external side effects?", "Write-capable tools can materially change risk mapping.", True),
            ],
            "D07": [
                ("mq_D07_rag_permissions", "high", "Is the RAG knowledge base filtered by user or tenant permissions?", "RAG permission filtering affects data exposure risks.", False),
            ],
            "D08": [
                ("mq_D08_connectors", "critical", "Does the Agent use MCP, A2A, custom connectors, WebSocket, SSE, browser automation, or code execution?", "Connector and protocol assets define external attack and trust boundaries.", True),
            ],
            "D09": [
                ("mq_D09_sensitive_data", "critical", "Does the Agent process PII, customer data, API keys, tokens, secrets, or credentials?", "Sensitive data and secret handling must be known before risk mapping.", True),
            ],
            "D10": [
                ("mq_D10_trust_boundaries", "critical", "Where do user input, RAG context, tool parameters, tool results, logs, and model context flow?", "Trust boundaries and data flow are required for risk mapping.", True),
            ],
            "D11": [
                ("mq_D11_memory", "high", "Does the Agent use short-term memory, long-term memory, state storage, or cross-session context?", "Memory and state affect persistence and cross-user exposure risks.", False),
            ],
        }
        return [
            {
                "id": question_id,
                "dimension_id": dimension_id,
                "related_capability_ids": ["F001"],
                "related_asset_ids": [],
                "priority": priority,
                "question": question,
                "reason": reason,
                "answer_type": "text",
                "options": [],
                "answer": "",
                "blocks_risk_mapping": blocks,
            }
            for question_id, priority, question, reason, blocks in question_map.get(dimension_id, [])
        ]

    def fallback_risk_hints(self, dimension_id: str) -> list[str]:
        hints = {
            "D02": ["Unknown service account or delegated identity may hide privilege escalation paths."],
            "D06": ["Unknown write-capable tools may create external side effects."],
            "D08": ["Unknown connector/protocol assets may cross trust boundaries."],
            "D09": ["Unknown secrets or tokens may create credential exposure risks."],
            "D10": ["Unknown data flow and storage boundaries can block accurate risk mapping."],
            "D11": ["Unknown memory/state behavior may persist malicious or sensitive context."],
        }
        return hints.get(dimension_id, [])

    def is_timeout_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return isinstance(error, (TimeoutError, socket.timeout)) or "timed out" in text or "timeout" in text

    def should_fallback_asset_review(self, error: Exception) -> bool:
        text = str(error).lower()
        transient_markers = (
            "invalid asset review json",
            "eof occurred in violation of protocol",
            "urlopen error",
            "remote end closed connection",
            "connection reset",
            "connection aborted",
            "ssl",
        )
        return self.is_timeout_error(error) or any(marker in text for marker in transient_markers)

    def image_part(self, path: Path) -> dict[str, Any]:
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "application/octet-stream")
        return {"inline_data": {"mime_type": mime, "data": base64.b64encode(path.read_bytes()).decode("ascii")}}

    def generate_json(
        self,
        prompt: str,
        expected_keys: list[str],
        images: list[dict[str, Any]],
        settings: dict[str, Any] | None = None,
        max_tokens: int = 8192,
        timeout: int = 300,
        repair: bool = True,
    ) -> dict[str, Any]:
        provider, model = self.resolve_model(settings)
        api_key = self.store.get_provider_api_key(provider)
        if not api_key:
            raise RuntimeError(f"{provider} API Key is not configured")
        text = self.request_model(prompt, images, provider, model, api_key, json_mode=True, max_tokens=max_tokens, timeout=timeout)
        parsed = self.parse_json_safe(text)
        if (not parsed or not self.has_keys(parsed, expected_keys)) and not repair:
            raise RuntimeError("Model returned invalid asset review JSON")
        if not parsed or not self.has_keys(parsed, expected_keys):
            repair_prompt = f"Repair this into valid JSON with keys {expected_keys}. Return JSON only:\n{text}"
            repaired = self.request_model(repair_prompt, [], provider, model, api_key, json_mode=True, max_tokens=max_tokens, timeout=min(timeout, 60))
            parsed = self.parse_json_safe(repaired)
        if not parsed:
            raise RuntimeError("Gemini returned content that could not be parsed as JSON after repair.")
        if not self.has_keys(parsed, expected_keys):
            raise RuntimeError("Gemini returned JSON that does not match the expected schema")
        return parsed

    def resolve_model(self, settings: dict[str, Any] | None) -> tuple[str, str]:
        provider = str((settings or {}).get("provider") or "gemini")
        model = str((settings or {}).get("modelName") or GEMINI_MODEL)
        return provider, model

    def request_model(self, prompt: str, images: list[dict[str, Any]], provider: str, model: str, api_key: str, json_mode: bool, max_tokens: int, timeout: int) -> str:
        if provider == "gemini":
            parts: list[dict[str, Any]] = [{"text": prompt}, *images]
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens},
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"
            return self.request_gemini(payload, api_key, model, timeout)
        if provider == "anthropic":
            return self.request_anthropic(prompt, images, api_key, model, max_tokens, timeout)
        return self.request_openai_compatible(prompt, images, provider, api_key, model, json_mode, max_tokens, timeout)

    def request_gemini(self, payload: dict[str, Any], api_key: str, model: str, timeout: int) -> str:
        url = GEMINI_ENDPOINT.format(model=model)
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.last_model_used = model
            candidates = data.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            return "\n".join(str(part.get("text") or "") for part in parts)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini request failed: {detail}") from error

    def request_openai_compatible(self, prompt: str, images: list[dict[str, Any]], provider: str, api_key: str, model: str, json_mode: bool, max_tokens: int, timeout: int) -> str:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            mime = image.get("inline_data", {}).get("mime_type") or "image/png"
            data = image.get("inline_data", {}).get("data") or ""
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            OPENAI_COMPATIBLE_ENDPOINTS[provider],
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.last_model_used = model
            return str((data.get("choices") or [{}])[0].get("message", {}).get("content") or "")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"{provider} request failed: {detail}") from error

    def request_anthropic(self, prompt: str, images: list[dict[str, Any]], api_key: str, model: str, max_tokens: int, timeout: int) -> str:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            mime = image.get("inline_data", {}).get("mime_type") or "image/png"
            data = image.get("inline_data", {}).get("data") or ""
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
        payload = {"model": model, "max_tokens": max_tokens, "temperature": 0.2, "messages": [{"role": "user", "content": content}]}
        request = urllib.request.Request(
            ANTHROPIC_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.last_model_used = model
            return "\n".join(str(item.get("text") or "") for item in data.get("content", []) if item.get("type") == "text")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Anthropic request failed: {detail}") from error

    def parse_json(self, text: str) -> dict[str, Any]:
        parsed = self.parse_json_safe(text)
        if parsed is None:
            raise json.JSONDecodeError("Unable to parse JSON", text, 0)
        return parsed

    def parse_json_safe(self, text: str) -> dict[str, Any] | None:
        cleaned = self.strip_json_wrappers(text)
        for candidate in [cleaned, self.extract_balanced_json(cleaned)]:
            if not candidate:
                continue
            try:
                value = json.loads(candidate)
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                continue
        return None

    def strip_json_wrappers(self, text: str) -> str:
        stripped = text.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
        if fence:
            return fence.group(1).strip()
        return stripped

    def extract_balanced_json(self, text: str) -> str:
        start = text.find("{")
        if start < 0:
            return ""
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return text[start:]

    def has_keys(self, value: dict[str, Any], keys: list[str]) -> bool:
        return isinstance(value, dict) and all(key in value for key in keys)

    def normalize_function_review(self, result: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
        result["projectId"] = result.get("projectId") or project["projectId"]
        result["projectName"] = result.get("projectName") or project.get("projectName", "")
        result["review_stage"] = result.get("review_stage") or "asset_review"
        result["schema_version"] = "2.0"
        result.setdefault("summary", "")
        result.setdefault("confidence", 0)
        result.setdefault("overall_confidence", result.get("confidence", 0))
        result.setdefault("project_summary", {"agent_type": project.get("agentType", ""), "review_status": "asset_review_completed"})
        result.setdefault("features", [])
        result["coverage_matrix"] = self.normalize_coverage_matrix(result.get("coverage_matrix") or [], result.get("features") or [], result.get("missing_questions") or [])
        result["features"] = self.normalize_capabilities(result.get("features") or [])
        result.setdefault("relationships", [])
        result.setdefault("asset_graph_nodes", [])
        result.setdefault("asset_graph_edges", [])
        should_build_graph = bool(
            result.get("agentAssetGraph")
            or result.get("asset_graph_nodes")
            or result.get("asset_graph_edges")
            or result.get("features")
        ) and result.get("review_stage") != "material_question_review"
        if should_build_graph:
            result["agentAssetGraph"] = normalize_agent_asset_graph(
                result.get("agentAssetGraph") or legacy_review_to_agent_asset_graph(result, project),
                result.get("projectName") or project.get("projectName", ""),
            )
            result["asset_graph_nodes"] = result.get("asset_graph_nodes") or result["agentAssetGraph"].get("assets", [])
            result["asset_graph_edges"] = result.get("asset_graph_edges") or result["agentAssetGraph"].get("relationships", [])
        else:
            result.pop("agentAssetGraph", None)
        result.setdefault("components", [])
        result.setdefault("capabilities", [])
        result.setdefault("dataFlows", [])
        result.setdefault("assumptions", [])
        result["missing_questions"] = self.normalize_missing_questions(result.get("missing_questions") or result.get("missingInformation") or [])
        result["missingInformation"] = [
            {"id": item.get("id"), "question": item.get("question", ""), "reason": item.get("reason", "")}
            for item in result["missing_questions"]
        ]
        result.setdefault("vueFlow", {"nodes": [], "edges": []})
        return result

    def normalize_coverage_matrix(self, matrix: list[dict[str, Any]], features: list[dict[str, Any]], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id = {str(item.get("dimension_id") or item.get("id") or ""): item for item in matrix if isinstance(item, dict)}
        valid_status = {"present", "partial", "missing", "unknown", "not_applicable", "high_risk"}
        status_aliases = {"missing_info": "partial", "not_found": "missing"}
        normalized = []
        for dimension_id, name, zh_name, description in ASSET_DIMENSIONS:
            item = by_id.get(dimension_id, {})
            related = item.get("related_capability_ids")
            if not isinstance(related, list):
                related = [
                    str(feature.get("id"))
                    for feature in features
                    if dimension_id in (feature.get("mapped_dimensions") or [])
                ]
            missing_fields = item.get("missing_fields") if isinstance(item.get("missing_fields"), list) else []
            unanswered_count = item.get("unanswered_question_count")
            if unanswered_count is None:
                unanswered_count = sum(1 for question in questions if question.get("dimension_id") == dimension_id and not question.get("answer"))
            status = str(item.get("status") or ("missing_info" if missing_fields or unanswered_count else "unknown"))
            status = status_aliases.get(status, status)
            detected_assets = self.normalize_detected_assets(item.get("detected_assets") or item.get("detected_items") or [], dimension_id)
            evidence = self.normalize_evidence(item.get("evidence") or [])
            normalized.append(
                {
                    "dimension_id": dimension_id,
                    "dimension_name": name,
                    "dimension_zh_name": zh_name,
                    "status": status if status in valid_status else "unknown",
                    "coverage_score": float(item.get("coverage_score") or item.get("confidence") or 0),
                    "confidence": float(item.get("confidence") or 0),
                    "summary": item.get("summary") or description,
                    "detected_assets": detected_assets,
                    "detected_items": [asset.get("name") for asset in detected_assets],
                    "missing_fields": missing_fields,
                    "evidence": evidence,
                    "related_capability_ids": related,
                    "related_graph_node_ids": item.get("related_graph_node_ids") if isinstance(item.get("related_graph_node_ids"), list) else related,
                    "unanswered_question_count": int(unanswered_count or 0),
                    "potential_risk_hints": item.get("potential_risk_hints") if isinstance(item.get("potential_risk_hints"), list) else [],
                }
            )
        return normalized

    def normalize_detected_assets(self, assets: list[Any], dimension_id: str) -> list[dict[str, Any]]:
        if not isinstance(assets, list):
            return []
        normalized = []
        risk_levels = {"none", "low", "medium", "high", "critical", "unknown"}
        for index, asset in enumerate(assets, start=1):
            if isinstance(asset, str):
                asset = {"name": asset, "description": asset}
            if not isinstance(asset, dict):
                continue
            risk_level = str(asset.get("risk_level") or "unknown")
            normalized.append(
                {
                    "asset_id": str(asset.get("asset_id") or f"asset_{dimension_id}_{index}"),
                    "asset_type": str(asset.get("asset_type") or "asset"),
                    "name": str(asset.get("name") or asset.get("asset_id") or f"Asset {index}"),
                    "description": str(asset.get("description") or ""),
                    "properties": asset.get("properties") if isinstance(asset.get("properties"), dict) else {},
                    "source_dimension_id": str(asset.get("source_dimension_id") or dimension_id),
                    "confidence": float(asset.get("confidence") or 0),
                    "risk_level": risk_level if risk_level in risk_levels else "unknown",
                }
            )
        return normalized

    def normalize_evidence(self, evidence: list[Any]) -> list[dict[str, Any]]:
        if not isinstance(evidence, list):
            return []
        normalized = []
        source_types = {"uploaded_file", "manual_input", "image", "inferred"}
        for index, item in enumerate(evidence, start=1):
            if isinstance(item, str):
                item = {"source_name": "Evidence", "excerpt": item, "source_type": "inferred"}
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type") or "inferred")
            normalized.append(
                {
                    "evidence_id": str(item.get("evidence_id") or f"ev_{index}"),
                    "source_type": source_type if source_type in source_types else "inferred",
                    "source_name": str(item.get("source_name") or ""),
                    "excerpt": str(item.get("excerpt") or ""),
                    "confidence": float(item.get("confidence") or 0),
                }
            )
        return normalized

    def normalize_capabilities(self, features: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for index, feature in enumerate(features, start=1):
            if not isinstance(feature, dict):
                continue
            item = dict(feature)
            item["id"] = str(item.get("id") or f"F{index:03d}")
            item.setdefault("mapped_dimensions", [])
            item.setdefault("related_asset_ids", [])
            item.setdefault("status", "present")
            for key in ("inputs", "outputs", "components", "external_systems", "data_assets", "permissions", "dependencies", "evidence", "missing_fields", "flow_next"):
                if not isinstance(item.get(key), list):
                    item[key] = []
            item.setdefault("tools", [])
            item.setdefault("rag", {"used": False, "knowledge_sources": [], "retrieval_conditions": [], "returns_citations": False})
            item.setdefault("file_or_image_processing", {"used": False, "types": [], "flow": ""})
            normalized.append(item)
        return normalized

    def normalize_missing_questions(self, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        priorities = {"critical", "high", "medium", "low"}
        answer_types = {"text", "single_choice", "multi_choice", "boolean"}
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                continue
            priority = str(question.get("priority") or "medium")
            answer_type = str(question.get("answer_type") or "text")
            normalized.append(
                {
                    "id": str(question.get("id") or f"mq_{index}"),
                    "dimension_id": str(question.get("dimension_id") or "D01"),
                    "related_capability_ids": question.get("related_capability_ids") if isinstance(question.get("related_capability_ids"), list) else [],
                    "related_asset_ids": question.get("related_asset_ids") if isinstance(question.get("related_asset_ids"), list) else [],
                    "priority": priority if priority in priorities else "medium",
                    "question": str(question.get("question") or ""),
                    "reason": str(question.get("reason") or ""),
                    "answer_type": answer_type if answer_type in answer_types else "text",
                    "options": question.get("options") if isinstance(question.get("options"), list) else [],
                    "answer": question.get("answer", ""),
                    "blocks_risk_mapping": bool(question.get("blocks_risk_mapping")),
                }
            )
        return normalized

    def normalize_risk_review(self, result: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
        result["projectId"] = result.get("projectId") or project["projectId"]
        result.setdefault("summary", "")
        result.setdefault("risks", [])
        result.setdefault("vueFlow", project.get("functionMap") or {"nodes": [], "edges": []})
        result.setdefault("reportMarkdown", "")
        return result
