from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: int = 1
    full_name: str
    email: str
    role: str
    organization: str
    phone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=256)
    email: str = Field(..., min_length=3, max_length=320)
    role: str = Field(..., min_length=2, max_length=128)
    organization: str = Field(..., min_length=2, max_length=64)
    phone: str = Field(default="", max_length=64)
