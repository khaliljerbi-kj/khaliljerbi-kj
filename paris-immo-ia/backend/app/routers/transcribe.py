from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..services.transcription import MAX_AUDIO_BYTES, TranscriptionUnavailable, transcribe

router = APIRouter(prefix="/api", tags=["audio"])


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> dict:
    """Reçoit l'enregistrement du bouton micro (webm/ogg/mp4/wav) et renvoie le texte."""
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(400, "Fichier audio vide")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Enregistrement trop long (25 Mo max)")
    content_type = (audio.content_type or "audio/webm").split(";")[0]
    if not content_type.startswith("audio/") and content_type != "video/webm":
        raise HTTPException(415, f"Type non supporté : {content_type}")
    try:
        text = await run_in_threadpool(transcribe, audio.filename or "dictee.webm", data, content_type)
    except TranscriptionUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"text": text}
