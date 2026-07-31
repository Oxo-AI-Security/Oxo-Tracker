import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.paths import DATA_ROOT


REVIEW_ROOT = DATA_ROOT / "agent-security-review"
GLOBAL_SETTINGS_FILE = REVIEW_ROOT / "settings.json"


MODEL_PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "apiKeyLabel": "Gemini API Key",
        "models": [
            {"label": "Gemini 3.5 Flash", "value": "gemini-3.5-flash"},
            {"label": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
            {"label": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"},
        ],
        "supported": ".pdf, .txt, .md, .json, .yaml, .png, .jpg, .jpeg, .webp; Word/Excel/CSV are converted to text locally.",
    },
    "openai": {
        "label": "OpenAI",
        "apiKeyLabel": "OpenAI API Key",
        "models": [
            {"label": "GPT-4.1", "value": "gpt-4.1"},
            {"label": "GPT-4.1 mini", "value": "gpt-4.1-mini"},
            {"label": "GPT-4o", "value": "gpt-4o"},
        ],
        "supported": ".pdf and images can be sent as model inputs; Word/Excel/CSV/Text are converted to text locally.",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "apiKeyLabel": "Anthropic API Key",
        "models": [
            {"label": "Claude Sonnet 4", "value": "claude-sonnet-4-20250514"},
            {"label": "Claude Opus 4.1", "value": "claude-opus-4-1-20250805"},
            {"label": "Claude 3.7 Sonnet", "value": "claude-3-7-sonnet-20250219"},
        ],
        "supported": ".pdf and images are native inputs; Word/Excel/CSV/Text are converted to text locally.",
    },
    "kimi": {
        "label": "Kimi",
        "apiKeyLabel": "Kimi API Key",
        "models": [
            {"label": "Kimi K2.5", "value": "kimi-k2.5"},
            {"label": "Moonshot V1 128K Vision", "value": "moonshot-v1-128k-vision-preview"},
            {"label": "Moonshot V1 128K", "value": "moonshot-v1-128k"},
        ],
        "supported": "Vision models support image input; Office/PDF/CSV/Text are converted to text locally for API review.",
    },
    "qwen": {
        "label": "Qwen",
        "apiKeyLabel": "DashScope API Key",
        "models": [
            {"label": "Qwen", "value": "qwen3.6-flash"},
            {"label": "Qwen", "value": "qwen3.6-plus"},
            {"label": "Qwen", "value": "qwen-long"},
        ],
        "supported": "Qwen file/document products support TXT, DOCX, PDF, XLSX, MD, CSV, JSON and common images; local conversion is used before API review.",
    },
}

DEFAULT_MODEL_SETTINGS = {"provider": "gemini", "modelName": "gemini-3.5-flash", "temperature": 0.2}


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_project_id(project_name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", project_name.strip().lower()).strip("-")
    if not base:
        base = "agent-review"
    return f"{base}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    return default


def write_json(path: Path, data: Any) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        data = {**data, "updatedAt": utc_now()}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


class AgentSecurityReviewStore:
    def __init__(self, root: Path = REVIEW_ROOT) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: str) -> Path:
        path = self.root / project_id
        if not path.exists():
            raise FileNotFoundError(project_id)
        return path

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_name = str(payload.get("projectName") or "Agent Security Review").strip()
        project_id = safe_project_id(project_name)
        path = self.root / project_id
        (path / "materials").mkdir(parents=True, exist_ok=True)
        now = utc_now()
        project = {
            "projectId": project_id,
            "projectName": project_name,
            "description": payload.get("description") or "",
            "agentType": payload.get("agentType") or "Chat Agent",
            "status": "draft",
            "materials": [],
            "manualInputs": {
                "systemPrompt": "",
                "toolList": "",
                "ragSource": "",
                "apiEndpointDescription": "",
                "extraNotes": "",
            },
            "missingAnswers": {},
            "createdAt": now,
            "updatedAt": now,
        }
        write_json(path / "project.json", project)
        write_json(path / "function-map.json", {"nodes": [], "edges": []})
        write_json(path / "risk-map.json", {"nodes": [], "edges": []})
        provider = str(payload.get("provider") or DEFAULT_MODEL_SETTINGS["provider"])
        model_name = str(payload.get("modelName") or DEFAULT_MODEL_SETTINGS["modelName"])
        write_json(
            path / "settings.json",
            {
                "provider": provider,
                "model": payload.get("model") or self.model_label(provider, model_name),
                "modelName": model_name,
                "temperature": 0.2,
                "apiKeyConfigured": bool(self.get_provider_api_key(provider)),
            },
        )
        return project

    def list_projects(self) -> list[dict[str, Any]]:
        projects = []
        for project_file in sorted(self.root.glob("*/project.json"), reverse=True):
            project = read_json(project_file, {})
            if project:
                projects.append(self.enrich_project(project["projectId"], project))
        return projects

    def get_project(self, project_id: str) -> dict[str, Any]:
        return self.enrich_project(project_id, read_json(self.project_dir(project_id) / "project.json", {}))

    def enrich_project(self, project_id: str, project: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        return {
            **project,
            "functionReview": read_json(path / "function-review.json", None),
            "functionMap": read_json(path / "function-map.json", {"nodes": [], "edges": []}),
            "assetGraph": read_json(path / "asset-graph.json", None),
            "assetLayout": read_json(path / "asset-layout.json", {}),
            "riskReview": read_json(path / "risk-review.json", None),
            "riskMap": read_json(path / "risk-map.json", {"nodes": [], "edges": []}),
            "reportMarkdown": (path / "report.md").read_text(encoding="utf-8") if (path / "report.md").exists() else "",
            "settings": read_json(path / "settings.json", {}),
        }

    def update_project(self, project_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        project = read_json(path / "project.json", {})
        project.update(changes)
        return write_json(path / "project.json", project)

    def begin_review_job(self, project_id: str, status: str) -> str:
        job_id = f"review-{uuid4().hex[:12]}"
        self.update_project(
            project_id,
            {
                "status": status,
                "error": "",
                "reviewJobId": job_id,
                "reviewCancelRequested": False,
                "reviewCancelledAt": "",
            },
        )
        return job_id

    def cancel_review_job(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        status = str(project.get("status") or "")
        if not self.is_review_status_busy(status):
            return project
        return self.update_project(
            project_id,
            {
                "status": "review_cancelled",
                "error": "Review cancelled by user.",
                "reviewCancelRequested": True,
                "reviewCancelledAt": utc_now(),
            },
        )

    def is_review_cancelled(self, project_id: str, job_id: str | None = None) -> bool:
        project = self.get_project(project_id)
        if job_id and project.get("reviewJobId") != job_id:
            return True
        return bool(project.get("reviewCancelRequested")) or project.get("status") == "review_cancelled"

    def is_review_status_busy(self, status: str) -> bool:
        return status in {
            "asset_review_running",
            "asset_review_gap_check_running",
            "asset_review_assets_running",
            "asset_review_capabilities_running",
            "asset_review_graph_running",
            "risk_reviewing",
        }

    async def add_material(self, project_id: str, upload: UploadFile, tag: str = "Other") -> dict[str, Any]:
        path = self.project_dir(project_id)
        materials_dir = path / "materials"
        materials_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(upload.filename or "material").suffix.lower()
        file_id = f"mat-{uuid4().hex[:12]}"
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(upload.filename or file_id).name).strip("-")
        stored_name = f"{file_id}-{safe_name or 'material'}"
        destination = materials_dir / stored_name
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        stat = destination.stat()
        image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        material = {
            "fileId": file_id,
            "fileName": upload.filename or stored_name,
            "storedName": stored_name,
            "tag": tag or "Other",
            "contentType": upload.content_type or "",
            "extension": suffix,
            "size": stat.st_size,
            "uploadedAt": utc_now(),
            "extractionSupported": suffix in {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".docx", ".xlsx", *image_extensions},
            "extractionMode": "visual" if suffix in image_extensions else "text",
        }
        project = read_json(path / "project.json", {})
        project["materials"] = [*project.get("materials", []), material]
        project["status"] = "materials_uploaded"
        write_json(path / "project.json", project)
        return material

    def delete_material(self, project_id: str, file_id: str) -> dict[str, Any]:
        path = self.project_dir(project_id)
        project = read_json(path / "project.json", {})
        material = next((item for item in project.get("materials", []) if item.get("fileId") == file_id), None)
        if not material:
            raise FileNotFoundError(file_id)
        file_path = path / "materials" / material["storedName"]
        if file_path.exists():
            file_path.unlink()
        project["materials"] = [item for item in project.get("materials", []) if item.get("fileId") != file_id]
        write_json(path / "project.json", project)
        return {"deleted": True, "fileId": file_id}

    def delete_project(self, project_id: str) -> dict[str, Any]:
        path = self.project_dir(project_id)
        shutil.rmtree(path)
        return {"deleted": True, "projectId": project_id}

    def save_model_settings(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        current = read_json(path / "settings.json", {})
        provider = str(payload.get("provider") or current.get("provider") or DEFAULT_MODEL_SETTINGS["provider"])
        model_name = str(payload.get("modelName") or current.get("modelName") or DEFAULT_MODEL_SETTINGS["modelName"])
        saved = write_json(
            path / "settings.json",
            {
                **current,
                "provider": provider,
                "modelName": model_name,
                "model": payload.get("model") or self.model_label(provider, model_name),
                "temperature": payload.get("temperature", current.get("temperature", 0.2)),
                "apiKeyConfigured": bool(self.get_provider_api_key(provider)),
            },
        )
        return saved

    def get_model_settings(self, project_id: str | None = None) -> dict[str, Any]:
        settings = DEFAULT_MODEL_SETTINGS.copy()
        if project_id:
            try:
                settings.update(read_json(self.project_dir(project_id) / "settings.json", {}))
            except FileNotFoundError:
                pass
        return settings

    def model_label(self, provider: str, model_name: str) -> str:
        for item in MODEL_PROVIDERS.get(provider, {}).get("models", []):
            if item.get("value") == model_name:
                return str(item.get("label"))
        return model_name

    def save_function_review(self, project_id: str, review: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        write_json(path / "function-review.json", review)
        write_json(path / "function-map.json", review.get("vueFlow") or {"nodes": [], "edges": []})
        if review.get("agentAssetGraph"):
            write_json(path / "asset-graph.json", review.get("agentAssetGraph"))
        current = read_json(path / "project.json", {})
        if self.has_unanswered_missing_questions(review, current.get("missingAnswers") or {}):
            status = "missing_info_required"
        elif review.get("agentAssetGraph"):
            status = "function_map_ready"
        else:
            status = "asset_review_questions_ready"
        self.update_project(project_id, {"status": status})
        return self.get_project(project_id)

    def save_function_map(self, project_id: str, graph: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        saved = write_json(path / "function-map.json", {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])})
        layout = {
            str(node.get("id")): node.get("position")
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and node.get("id") and isinstance(node.get("position"), dict)
        }
        write_json(path / "asset-layout.json", layout)
        self.update_project(project_id, {"status": "function_map_ready"})
        return saved

    def save_risk_review(self, project_id: str, review: dict[str, Any]) -> dict[str, Any]:
        path = self.project_dir(project_id)
        write_json(path / "risk-review.json", review)
        write_json(path / "risk-map.json", review.get("vueFlow") or {"nodes": [], "edges": []})
        (path / "report.md").write_text(str(review.get("reportMarkdown") or ""), encoding="utf-8")
        self.update_project(project_id, {"status": "risk_map_ready"})
        return self.get_project(project_id)

    def save_manual_context(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for field in ("projectName", "description", "agentType"):
            if field in payload:
                changes[field] = payload[field]
        if "manualInputs" in payload:
            changes["manualInputs"] = payload["manualInputs"]
        if "missingAnswers" in payload:
            changes["missingAnswers"] = payload["missingAnswers"]
            try:
                current = self.get_project(project_id)
                if self.has_blocking_missing_questions(current.get("functionReview") or {}, payload["missingAnswers"]):
                    changes.setdefault("status", "missing_info_required")
                elif current.get("functionReview"):
                    changes.setdefault("status", "missing_info_answered")
            except FileNotFoundError:
                pass
        if changes:
            self.update_project(project_id, changes)
        if "functionMap" in payload:
            self.save_function_map(project_id, payload["functionMap"])
        return self.get_project(project_id)

    def has_blocking_missing_questions(self, review: dict[str, Any], answers: dict[str, Any] | None = None) -> bool:
        answer_lookup = answers or {}
        for question in review.get("missing_questions") or []:
            question_id = str(question.get("id") or "")
            answer = answer_lookup.get(question_id, question.get("answer"))
            if question.get("blocks_risk_mapping") and question.get("priority") == "critical" and not answer:
                return True
        return False

    def has_unanswered_missing_questions(self, review: dict[str, Any], answers: dict[str, Any] | None = None) -> bool:
        answer_lookup = answers or {}
        for question in review.get("missing_questions") or []:
            question_id = str(question.get("id") or "")
            answer = answer_lookup.get(question_id, question.get("answer"))
            if not str(answer or "").strip():
                return True
        return False

    def save_gemini_api_key(self, api_key: str) -> dict[str, Any]:
        return self.save_provider_api_key("gemini", api_key)

    def get_gemini_api_key(self) -> str:
        return self.get_provider_api_key("gemini")

    def save_provider_api_key(self, provider: str, api_key: str) -> dict[str, Any]:
        settings = read_json(GLOBAL_SETTINGS_FILE, {})
        keys = settings.get("apiKeys") or {}
        if api_key:
            keys[provider] = api_key
        saved = write_json(GLOBAL_SETTINGS_FILE, {**settings, "apiKeys": keys, f"{provider}ApiKeyConfigured": bool(keys.get(provider))})
        return {"apiKeyConfigured": bool((saved.get("apiKeys") or {}).get(provider)), "provider": provider}

    def get_provider_api_key(self, provider: str) -> str:
        settings = read_json(GLOBAL_SETTINGS_FILE, {})
        keys = settings.get("apiKeys") or {}
        if provider == "gemini" and settings.get("geminiApiKey"):
            return str(settings.get("geminiApiKey") or "")
        return str(keys.get(provider) or "")
