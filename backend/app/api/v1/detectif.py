
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.services.detectif_service import detect_deepfake

router = APIRouter(prefix="/v1/detectif", tags=["Detectif.ai"])


@router.post("/analyze")
async def analyze_audio_with_detectif(
    file: UploadFile = File(...),
):
    settings = get_settings()

    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if len(audio_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Audio file exceeds the configured upload limit.",
        )

    return await detect_deepfake(
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.wav",
        content_type=file.content_type or "application/octet-stream",
    )
