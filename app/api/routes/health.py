from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check(challenge: str | None = None) -> dict:
    response = {"status": "ok"}
    if challenge is not None:
        response["challenge"] = challenge
    return response
