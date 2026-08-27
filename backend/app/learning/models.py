import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..db import Base


class LearningLessonStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class LearningLesson(Base):
    __tablename__ = "learning_lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    level = Column(String(20), nullable=False)
    domain = Column(String(100), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(
        Enum(LearningLessonStatus, native_enum=False),
        nullable=False,
        default=LearningLessonStatus.draft,
        index=True,
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    thumbnail_original_filename = Column(String(255), nullable=True)
    thumbnail_storage_key = Column(String(1024), nullable=True, unique=True)
    thumbnail_content_type = Column(String(100), nullable=True)
    thumbnail_size_bytes = Column(Integer, nullable=True)

    videos = relationship(
        "LearningVideo",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LearningVideo.position, LearningVideo.id",
    )
    segments = relationship(
        "LearningSegment",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LearningSegment.position, LearningSegment.id",
    )
    vocabulary = relationship(
        "LearningVocabularyItem",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LearningVocabularyItem.position, LearningVocabularyItem.id",
    )
    grammar = relationship(
        "LearningGrammarItem",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LearningGrammarItem.position, LearningGrammarItem.id",
    )
    progress_records = relationship("LearningProgress", back_populates="lesson", cascade="all, delete-orphan")

    @property
    def thumbnail_url(self) -> str | None:
        return f"/api/learning/lessons/{self.id}/thumbnail" if self.thumbnail_storage_key else None


class LearningVideo(Base):
    __tablename__ = "learning_videos"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(
        Integer,
        ForeignKey("learning_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(1024), nullable=False, unique=True)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    source_url = Column(String(2048), nullable=True)
    source_link_label = Column(String(120), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lesson = relationship("LearningLesson", back_populates="videos")


class LearningSegment(Base):
    __tablename__ = "learning_segments"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("learning_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    start_ms = Column(Integer, nullable=True)
    end_ms = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    translation = Column(Text, nullable=False, default="")

    lesson = relationship("LearningLesson", back_populates="segments")
    blanks = relationship(
        "LearningBlank",
        back_populates="segment",
        cascade="all, delete-orphan",
        order_by="LearningBlank.position, LearningBlank.id",
    )


class LearningBlank(Base):
    __tablename__ = "learning_blanks"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("learning_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    answer = Column(String(255), nullable=False)
    accepted_variants = Column(JSON, nullable=False, default=list)
    accept_mutations = Column(Boolean, nullable=False, default=False)

    segment = relationship("LearningSegment", back_populates="blanks")


class LearningVocabularyItem(Base):
    __tablename__ = "learning_vocabulary_items"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("learning_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    term = Column(String(255), nullable=False)
    translation = Column(String(500), nullable=False)
    note = Column(Text, nullable=False, default="")

    lesson = relationship("LearningLesson", back_populates="vocabulary")


class LearningGrammarItem(Base):
    __tablename__ = "learning_grammar_items"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("learning_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    example = Column(Text, nullable=False, default="")
    translation = Column(Text, nullable=False, default="")

    lesson = relationship("LearningLesson", back_populates="grammar")


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_learning_progress_user_lesson"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("learning_lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="started")
    best_score = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lesson = relationship("LearningLesson", back_populates="progress_records")
