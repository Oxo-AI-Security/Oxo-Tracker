from fastapi import APIRouter

from app.integrations.moonshot.client import MoonshotClient

router = APIRouter(prefix="/moonshot", tags=["Moonshot"])


@router.get("/endpoints")
def list_endpoints() -> list[dict]:
    return MoonshotClient().list_endpoints()


@router.get("/recipes")
def list_recipes() -> list[dict]:
    return MoonshotClient().list_recipes()


@router.get("/cookbooks")
def list_cookbooks() -> list[dict]:
    return MoonshotClient().list_cookbooks()

