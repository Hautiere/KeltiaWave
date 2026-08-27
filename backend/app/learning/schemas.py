from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import LearningLessonStatus


class LearningVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    duration_seconds: int | None = None
    source_url: str | None = None
    source_link_label: str | None = None
    position: int
    created_at: datetime
    updated_at: datetime
    media_url: str | None = None


class LearningVideoUpdate(BaseModel):
    duration_seconds: int | None = Field(default=None, ge=0)
    position: int | None = Field(default=None, ge=0)
    source_url: str | None = Field(default=None, max_length=2048)
    source_link_label: str | None = Field(default=None, max_length=120)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("source_url must use http or https")
        return value

    @field_validator("source_link_label")
    @classmethod
    def normalize_source_link_label(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class LearningBlankWrite(BaseModel):
    position: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=255)
    accepted_variants: list[str] = Field(default_factory=list, max_length=20)
    accept_mutations: bool = False

    @field_validator("answer")
    @classmethod
    def strip_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("answer must not be empty")
        return value

    @field_validator("accepted_variants")
    @classmethod
    def normalize_accepted_variants(cls, values: list[str]) -> list[str]:
        output: list[str] = []
        for value in values:
            value = value.strip()
            if value and value not in output:
                output.append(value)
        return output


class LearningBlankRead(LearningBlankWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LearningSegmentWrite(BaseModel):
    position: int = Field(ge=0)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    text: str = Field(min_length=1)
    translation: str = ""
    blanks: list[LearningBlankWrite] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value

    @field_validator("translation")
    @classmethod
    def strip_translation(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_timestamps_and_blanks(self):
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        for blank in self.blanks:
            if blank.position >= len(self.text):
                raise ValueError("blank position is outside segment text")
        if len({blank.position for blank in self.blanks}) != len(self.blanks):
            raise ValueError("blank positions must be unique within a segment")
        return self


class LearningSegmentRead(LearningSegmentWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    blanks: list[LearningBlankRead] = Field(default_factory=list)


class LearningVocabularyWrite(BaseModel):
    position: int = Field(ge=0)
    term: str = Field(min_length=1, max_length=255)
    translation: str = Field(min_length=1, max_length=500)
    note: str = ""

    @field_validator("term", "translation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class LearningVocabularyRead(LearningVocabularyWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LearningGrammarWrite(BaseModel):
    position: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=255)
    explanation: str = Field(min_length=1)
    example: str = ""
    translation: str = ""

    @field_validator("title", "explanation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class LearningGrammarRead(LearningGrammarWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LearningLessonBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    level: str = Field(min_length=1, max_length=20)
    domain: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)

    @field_validator("title", "level", "domain")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class LearningLessonCreate(LearningLessonBase):
    segments: list[LearningSegmentWrite] = Field(default_factory=list)
    vocabulary: list[LearningVocabularyWrite] = Field(default_factory=list)
    grammar: list[LearningGrammarWrite] = Field(default_factory=list)


class LearningLessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    level: str | None = Field(default=None, min_length=1, max_length=20)
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    segments: list[LearningSegmentWrite] | None = None
    vocabulary: list[LearningVocabularyWrite] | None = None
    grammar: list[LearningGrammarWrite] | None = None

    @field_validator("title", "level", "domain")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class LearningLessonRead(LearningLessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: LearningLessonStatus
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    thumbnail_url: str | None = None
    videos: list[LearningVideoRead] = Field(default_factory=list)
    segments: list[LearningSegmentRead] = Field(default_factory=list)
    vocabulary: list[LearningVocabularyRead] = Field(default_factory=list)
    grammar: list[LearningGrammarRead] = Field(default_factory=list)


class LearningProgressWrite(BaseModel):
    status: str = Field(pattern="^(started|completed)$")
    score: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_score(self):
        if self.score > self.total_questions:
            raise ValueError("score cannot exceed total_questions")
        return self


class LearningProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    status: str
    best_score: int
    total_questions: int
    attempts: int
    started_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime
