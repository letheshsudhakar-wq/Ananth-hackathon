import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_session
from app.db.models import DetectifAnalysis
from app.services.detectif_service import detect_deepfake

router = APIRouter(prefix="/v1/detectif", tags=["Detectif.ai"])


@router.post("/analyze")
async def analyze_audio_with_detectif(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
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

    provider_response = await detect_deepfake(
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.wav",
        content_type=file.content_type or "application/octet-stream",
    )

    if not isinstance(provider_response, dict):
        raise HTTPException(
            status_code=502,
            detail="Detectif returned an invalid response.",
        )

    result = provider_response.get("result")

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="Detectif response is missing its result object.",
        )

    label = result.get("label")
    is_synthetic = result.get("is_synthetic")
    score = result.get("score")
    threshold = result.get("threshold")
    duration = result.get("duration_seconds")
    scored_duration = result.get("scored_seconds")

    if (
        label not in ("genuine", "synthetic")
        or not isinstance(is_synthetic, bool)
        or is_synthetic != (label == "synthetic")
        or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in (score, threshold, duration, scored_duration)
        )
        or not 0 <= score <= 1
        or not 0 <= threshold <= 1
        or duration <= 0
        or scored_duration < 0
    ):
        raise HTTPException(
            status_code=502,
            detail="Detectif returned incomplete or invalid analysis values.",
        )

    original_filename = (file.filename or "audio.wav").replace("\\", "/")
    safe_filename = os.path.basename(original_filename)[:255] or "audio.wav"

    request_id = provider_response.get("request_id")
    operation_id = provider_response.get("operation_id")

    if request_id is not None and not isinstance(request_id, str):
        raise HTTPException(status_code=502, detail="Invalid Detectif request ID.")

    if operation_id is not None and not isinstance(operation_id, str):
        raise HTTPException(status_code=502, detail="Invalid Detectif operation ID.")

    record = DetectifAnalysis(
        provider_request_id=request_id,
        operation_id=operation_id,
        filename=safe_filename,
        label=label,
        is_synthetic=is_synthetic,
        score=float(score),
        threshold=float(threshold),
        duration_seconds=float(duration),
        scored_seconds=float(scored_duration),
    )

    try:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Analysis completed, but its result could not be saved.",
        ) from exc

    response = dict(provider_response)
    response["analysis_id"] = record.analysis_id
    return response


@router.get("/history")
async def get_detectif_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    statement = (
        select(DetectifAnalysis)
        .order_by(desc(DetectifAnalysis.created_at), desc(DetectifAnalysis.id))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(statement)
    records = result.scalars().all()

    return {
        "items": [
            {
                "analysis_id": record.analysis_id,
                "request_id": record.provider_request_id,
                "operation_id": record.operation_id,
                "filename": record.filename,
                "label": record.label,
                "is_synthetic": record.is_synthetic,
                "score": record.score,
                "threshold": record.threshold,
                "duration_seconds": record.duration_seconds,
                "scored_seconds": record.scored_seconds,
                "created_at": record.created_at,
            }
            for record in records
        ],
        "limit": limit,
        "offset": offset,
        "returned": len(records),
    }


@router.get("/stats")
async def get_detectif_stats(
    session: AsyncSession = Depends(get_session),
):
    statement = select(
        func.count(DetectifAnalysis.id),
        func.sum(
            case((DetectifAnalysis.is_synthetic.is_(True), 1), else_=0)
        ),
        func.sum(
            case((DetectifAnalysis.is_synthetic.is_(False), 1), else_=0)
        ),
        func.avg(DetectifAnalysis.score),
        func.max(DetectifAnalysis.created_at),
    )

    result = await session.execute(statement)
    total, synthetic, genuine, average_score, latest = result.one()

    total = total or 0
    synthetic = synthetic or 0
    genuine = genuine or 0

    return {
        "total": total,
        "synthetic_count": synthetic,
        "genuine_count": genuine,
        "synthetic_percentage": round((synthetic / total) * 100, 2) if total else 0,
        "average_score": round(float(average_score), 6) if average_score is not None else None,
        "latest_analysis_at": latest,
    }
