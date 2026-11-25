from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.repositories import ProfileRepository
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/v1", tags=["profile"])


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(session: AsyncSession = Depends(get_session)) -> ProfileResponse:
    return await ProfileRepository(session).get()


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    return await ProfileRepository(session).update(payload.model_dump())
