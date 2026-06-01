from fastapi import APIRouter, Body

from app.services.settings_store import SettingsStore

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_settings() -> dict:
    return SettingsStore().get()


@router.patch("")
def update_settings(data: dict = Body(...)) -> dict:
    return SettingsStore().update(data)
