# backend/app/models/audio.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from datetime import datetime
from ..db import Base
from sqlalchemy.orm import relationship
import enum

class AudioStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class Audio(Base):
    __tablename__ = "audios"

    id = Column(Integer, primary_key=True, index=True)
    phrase_id = Column(Integer, ForeignKey("phrases.id"), nullable=False)
    filename = Column(String, nullable=False)
    origin = Column(String, default="user", nullable=False)
    status = Column(Enum(AudioStatus), default=AudioStatus.pending, nullable=False)
    phrase_source = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    speaker_region = Column(String, nullable=True)
    speaker_city = Column(String, nullable=True)
    speaker_accent = Column(String, nullable=True)
    speaker_level = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(String, nullable=True)
    validator_role = Column(String, nullable=True)
    validation_weight = Column(String, nullable=True)
    validation_comment = Column(String, nullable=True)
    contributor_name = Column(String, nullable=True)
    contributor_email = Column(String, nullable=True)
    contributor_school = Column(String, nullable=True)
    contributor_school_level = Column(String, nullable=True)
    validations = relationship(
        "AudioValidation",
        back_populates="audio",
        cascade="all, delete-orphan",
        order_by="AudioValidation.created_at.desc()",
    )


class AudioValidation(Base):
    __tablename__ = "audio_validations"

    id = Column(Integer, primary_key=True, index=True)
    audio_id = Column(Integer, ForeignKey("audios.id"), nullable=False, index=True)
    decision = Column(String, nullable=False)
    validator = Column(String, nullable=True)
    validator_role = Column(String, nullable=True)
    validation_weight = Column(String, nullable=True)
    pronunciation_level = Column(String, nullable=True)
    pronunciation_region = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    audio = relationship("Audio", back_populates="validations")
