from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import AnalysisEvidence

router = APIRouter(prefix="/v1", tags=["analytics"])


@router.get("/analytics")
async def get_analytics(
    days: int = Query(30, ge=7, le=90),
    organization: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    to_ts = datetime.now(timezone.utc)
    from_ts = to_ts - timedelta(days=days)
    stmt = select(AnalysisEvidence).where(AnalysisEvidence.created_at >= from_ts)
    if organization:
        stmt = stmt.where(AnalysisEvidence.organization == organization)

    result = await session.execute(stmt.order_by(AnalysisEvidence.created_at.asc()))
    records = result.scalars().all()

    total = len(records)
    safe_count = sum(
        1 for r in records
        if not r.flagged and (r.risk_score is None or r.risk_score < 50)
    )
    threat_count = total - safe_count
    safe_rate = (safe_count / total * 100) if total else 0
    threat_rate = (threat_count / total * 100) if total else 0

    confidences = [r.confidence for r in records if r.confidence is not None]
    confidence = (
        sum(confidences) / len(confidences) * 100
        if confidences
        else 0
    )
    latencies = [
        r.processing_latency_ms
        for r in records
        if r.processing_latency_ms is not None
    ]
    average_time_seconds = (
        sum(latencies) / len(latencies) / 1000
        if latencies
        else 0
    )

    grouped: dict[str, dict[str, int]] = {}
    for record in records:
        day = record.created_at.date().isoformat()
        bucket = grouped.setdefault(day, {"safe": 0, "threat": 0, "activity": 0})
        bucket["activity"] += 1
        is_safe = not record.flagged and (
            record.risk_score is None or record.risk_score < 50
        )
        bucket["safe" if is_safe else "threat"] += 1

    trend = [
        {"day": day, "safe": values["safe"], "threat": values["threat"], "activity": values["activity"]}
        for day, values in sorted(grouped.items())
    ]

    return {
        "days": days,
        "from_ts": from_ts.isoformat(),
        "to_ts": to_ts.isoformat(),
        "total": total,
        "safe_rate": round(safe_rate, 1),
        "threat_rate": round(threat_rate, 1),
        "confidence": round(confidence, 1),
        "average_time_seconds": round(average_time_seconds, 3),
        "trend": trend,
    }
