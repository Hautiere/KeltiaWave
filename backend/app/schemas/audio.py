# backend/app/schemas/audio.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from ..models.audio import AudioStatus

class AudioValidationRead(BaseModel):
    id: int
    audio_id: int
    decision: str
    validator: Optional[str] = None
    validator_role: Optional[str] = None
    validation_weight: Optional[str] = None
    pronunciation_level: Optional[str] = None
    pronunciation_region: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AudioRead(BaseModel):
    id: int
    phrase_id: int
    filename: str
    origin: str = "user"
    status: AudioStatus
    phrase_source: Optional[str] = None
    domain: Optional[str] = None
    speaker_region: Optional[str] = None
    speaker_city: Optional[str] = None
    speaker_accent: Optional[str] = None
    speaker_level: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None
    validator_role: Optional[str] = None
    validation_weight: Optional[str] = None
    validation_comment: Optional[str] = None
    contributor_name: Optional[str] = None
    contributor_email: Optional[str] = None
    contributor_school: Optional[str] = None
    contributor_school_level: Optional[str] = None
    validations: list[AudioValidationRead] = Field(default_factory=list)

    class Config:
        from_attributes = True  # permet de créer un schéma à partir d'un objet SQLAlchemy
