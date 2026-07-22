from fastapi import APIRouter, Body, HTTPException, Response

from app.services.ai_connection_service import probe_ai_connection
from app.services.settings_store import SettingsStore

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_settings() -> dict:
    return SettingsStore().get()


@router.patch("")
def update_settings(data: dict = Body(...)) -> dict:
    try:
        return SettingsStore().update(data)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/ai/api-key/reveal")
def reveal_ai_provider_api_key(response: Response, data: dict = Body(...)) -> dict:
    provider_id = str(data.get("provider") or "").strip()
    try:
        api_key = SettingsStore().get_provider_api_key(provider_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not api_key:
        raise HTTPException(status_code=404, detail="No API key is configured for this provider")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return {"provider": provider_id, "apiKey": api_key}


@router.post("/ai/test-connection")
def test_ai_provider_connection(data: dict = Body(...)) -> dict:
    provider_id = str(data.get("provider") or "").strip()
    model = str(data.get("model") or "").strip()
    base_url = str(data.get("baseUrl") or "").strip()
    api_key = str(data.get("apiKey") or "").strip()
    try:
        if not api_key:
            api_key = SettingsStore().get_provider_api_key(provider_id)
        return probe_ai_connection(provider_id, model, base_url, api_key)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
