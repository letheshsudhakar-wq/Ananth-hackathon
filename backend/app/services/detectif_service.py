
import uuid

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


async def detect_deepfake(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
) -> dict:
    settings = get_settings()

    if not settings.DETECTIF_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Detectif API key is not configured.",
        )

    url = (
        f"{settings.DETECTIF_BASE_URL.rstrip('/')}"
        "/v1/deepfake/detect"
    )

    headers = {
        "Authorization": f"Bearer {settings.DETECTIF_API_KEY}",
        "Idempotency-Key": str(uuid.uuid4()),
    }

    files = {
        "file": (
            filename or "audio.wav",
            audio_bytes,
            content_type or "application/octet-stream",
        )
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                url,
                headers=headers,
                files=files,
            )

        if response.is_error:
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "message": "Detectif API returned an error.",
                    "provider_response": response.text[:1000],
                },
            )

        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Detectif API request timed out.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Detectif API.",
        )
