from ..config import get_settings

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # limite de l'API Whisper


class TranscriptionUnavailable(RuntimeError):
    pass


def transcription_available() -> bool:
    return bool(get_settings().openai_api_key)


def transcribe(filename: str, data: bytes, content_type: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise TranscriptionUnavailable("OPENAI_API_KEY manquant : utilisez la dictée du navigateur.")
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key, timeout=60)
    result = client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=(filename, data, content_type),
        language="fr",
        prompt="Recherche d'appartement à Paris : arrondissements, quartiers, métro, loyer charges comprises.",
    )
    return result.text.strip()
