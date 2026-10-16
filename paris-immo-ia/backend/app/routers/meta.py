from dataclasses import asdict

from fastapi import APIRouter

from ..knowledge.paris import quartiers
from ..services.llm import get_provider
from ..services.transcription import transcription_available

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": get_provider().name,
        "server_transcription": transcription_available(),
    }


@router.get("/quartiers")
def list_quartiers() -> list[dict]:
    return [asdict(q) for q in quartiers().values()]
