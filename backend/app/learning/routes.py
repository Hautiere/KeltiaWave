from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user, get_optional_user, require_admin
from ..db import get_db
from ..models.user import User
from .models import (
    LearningBlank,
    LearningGrammarItem,
    LearningLesson,
    LearningLessonStatus,
    LearningProgress,
    LearningSegment,
    LearningVideo,
    LearningVocabularyItem,
)
from .schemas import (
    LearningLessonCreate,
    LearningLessonRead,
    LearningLessonUpdate,
    LearningProgressRead,
    LearningProgressWrite,
    LearningVideoRead,
    LearningVideoUpdate,
)
from .storage import (
    delete_learning_thumbnail,
    delete_learning_video,
    learning_thumbnail_response,
    learning_video_response,
    save_learning_thumbnail,
    save_learning_video,
)


router = APIRouter()


@router.get("/progress", response_model=list[LearningProgressRead])
def list_my_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(LearningProgress).filter(LearningProgress.user_id == user.id).order_by(LearningProgress.updated_at.desc()).all()


@router.put("/lessons/{lesson_id}/progress", response_model=LearningProgressRead)
def save_my_progress(
    lesson_id: int,
    payload: LearningProgressWrite,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _lesson_or_404(db, lesson_id)
    if lesson.status != LearningLessonStatus.published:
        raise HTTPException(status_code=404, detail="Learning lesson not found")
    progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == user.id,
        LearningProgress.lesson_id == lesson_id,
    ).first()
    if not progress:
        progress = LearningProgress(user_id=user.id, lesson_id=lesson_id)
        db.add(progress)
    progress.status = "completed" if payload.status == "completed" or progress.status == "completed" else "started"
    progress.best_score = max(progress.best_score or 0, payload.score)
    progress.total_questions = max(progress.total_questions or 0, payload.total_questions)
    if payload.status == "completed":
        progress.attempts = (progress.attempts or 0) + 1
        progress.completed_at = datetime.utcnow()
    progress.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(progress)
    return progress


def _lesson_query(db: Session):
    return db.query(LearningLesson).options(
        selectinload(LearningLesson.videos),
        selectinload(LearningLesson.segments).selectinload(LearningSegment.blanks),
        selectinload(LearningLesson.vocabulary),
        selectinload(LearningLesson.grammar),
    )


def _lesson_or_404(db: Session, lesson_id: int) -> LearningLesson:
    lesson = _lesson_query(db).filter(LearningLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Learning lesson not found")
    return lesson


def _can_manage(user: User | None) -> bool:
    return bool(user and user.role == "admin")


def _replace_content(lesson: LearningLesson, payload: dict) -> None:
    if "segments" in payload:
        lesson.segments = [
            LearningSegment(
                position=item.position,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                text=item.text,
                translation=item.translation,
                blanks=[LearningBlank(**blank.model_dump()) for blank in item.blanks],
            )
            for item in payload.pop("segments")
        ]
    if "vocabulary" in payload:
        lesson.vocabulary = [
            LearningVocabularyItem(**item.model_dump()) for item in payload.pop("vocabulary")
        ]
    if "grammar" in payload:
        lesson.grammar = [
            LearningGrammarItem(**item.model_dump()) for item in payload.pop("grammar")
        ]


@router.get("/lessons", response_model=list[LearningLessonRead])
def list_lessons(
    include_unpublished: bool = False,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    query = _lesson_query(db)
    if include_unpublished:
        if not _can_manage(user):
            raise HTTPException(status_code=403, detail="Admin role required")
    else:
        query = query.filter(LearningLesson.status == LearningLessonStatus.published)
    return query.order_by(LearningLesson.created_at.desc(), LearningLesson.id.desc()).all()


@router.post("/lessons", response_model=LearningLessonRead, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: LearningLessonCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(exclude={"segments", "vocabulary", "grammar"})
    lesson = LearningLesson(**values, created_by_id=admin.id)
    content = {
        "segments": payload.segments,
        "vocabulary": payload.vocabulary,
        "grammar": payload.grammar,
    }
    _replace_content(lesson, content)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/lessons/{lesson_id}", response_model=LearningLessonRead)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    lesson = _lesson_or_404(db, lesson_id)
    if lesson.status != LearningLessonStatus.published and not _can_manage(user):
        raise HTTPException(status_code=404, detail="Learning lesson not found")
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LearningLessonRead)
def update_lesson(
    lesson_id: int,
    payload: LearningLessonUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lesson = _lesson_or_404(db, lesson_id)
    values = payload.model_dump(
        exclude_unset=True,
        exclude={"segments", "vocabulary", "grammar"},
    )
    content = {
        key: getattr(payload, key)
        for key in ("segments", "vocabulary", "grammar")
        if key in payload.model_fields_set
    }
    _replace_content(lesson, content)
    for key, value in values.items():
        setattr(lesson, key, value)
    lesson.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson


def _change_status(db: Session, lesson_id: int, lesson_status: LearningLessonStatus) -> LearningLesson:
    lesson = _lesson_or_404(db, lesson_id)
    if lesson_status == LearningLessonStatus.published and not lesson.videos:
        raise HTTPException(status_code=409, detail="A lesson needs at least one video before publication")
    if lesson_status == LearningLessonStatus.published and not lesson.segments:
        raise HTTPException(status_code=409, detail="A lesson needs at least one segment before publication")
    if lesson_status == LearningLessonStatus.published and not any(segment.blanks for segment in lesson.segments):
        raise HTTPException(status_code=409, detail="A lesson needs at least one blank before publication")
    lesson.status = lesson_status
    lesson.published_at = datetime.utcnow() if lesson_status == LearningLessonStatus.published else None
    lesson.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson


@router.post("/lessons/{lesson_id}/publish", response_model=LearningLessonRead)
def publish_lesson(
    lesson_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _change_status(db, lesson_id, LearningLessonStatus.published)


@router.post("/lessons/{lesson_id}/archive", response_model=LearningLessonRead)
def archive_lesson(
    lesson_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _change_status(db, lesson_id, LearningLessonStatus.archived)


@router.post("/lessons/{lesson_id}/thumbnail", response_model=LearningLessonRead)
async def upload_lesson_thumbnail(
    lesson_id: int,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lesson = _lesson_or_404(db, lesson_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Thumbnail file is missing")
    stored = await save_learning_thumbnail(file, lesson_id)
    previous_key = lesson.thumbnail_storage_key
    lesson.thumbnail_original_filename = file.filename
    lesson.thumbnail_storage_key = str(stored["storage_key"])
    lesson.thumbnail_content_type = file.content_type or "application/octet-stream"
    lesson.thumbnail_size_bytes = int(stored["size_bytes"])
    lesson.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(lesson)
    except Exception:
        db.rollback()
        delete_learning_thumbnail(str(stored["storage_key"]))
        raise
    if previous_key and previous_key != lesson.thumbnail_storage_key:
        delete_learning_thumbnail(previous_key)
    return lesson


@router.get("/lessons/{lesson_id}/thumbnail")
def get_lesson_thumbnail(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    lesson = _lesson_or_404(db, lesson_id)
    if lesson.status != LearningLessonStatus.published and not _can_manage(user):
        raise HTTPException(status_code=404, detail="Learning thumbnail not found")
    if not lesson.thumbnail_storage_key or not lesson.thumbnail_content_type:
        raise HTTPException(status_code=404, detail="Learning thumbnail not found")
    return learning_thumbnail_response(lesson.thumbnail_storage_key, lesson.thumbnail_content_type)


@router.post(
    "/lessons/{lesson_id}/videos",
    response_model=LearningVideoRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(
    lesson_id: int,
    file: UploadFile = File(...),
    duration_seconds: int | None = Form(None, ge=0),
    position: int = Form(0, ge=0),
    replace_existing: bool = Form(False),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _lesson_or_404(db, lesson_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Video file is missing")

    existing_videos = list(db.query(LearningVideo).filter(LearningVideo.lesson_id == lesson_id).all()) if replace_existing else []
    existing_storage_keys = [existing.storage_key for existing in existing_videos]
    stored = await save_learning_video(file, lesson_id)
    video = LearningVideo(
        lesson_id=lesson_id,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        duration_seconds=duration_seconds,
        position=position,
        **stored,
    )
    try:
        db.add(video)
        for existing in existing_videos:
            db.delete(existing)
        db.commit()
        db.refresh(video)
    except Exception:
        db.rollback()
        delete_learning_video(str(stored["storage_key"]))
        raise
    for storage_key in existing_storage_keys:
        delete_learning_video(storage_key)
    return video


@router.get("/videos/{video_id}/file")
def get_video_file(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    video = db.query(LearningVideo).filter(LearningVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Learning video not found")
    if video.lesson.status != LearningLessonStatus.published and not _can_manage(user):
        raise HTTPException(status_code=404, detail="Learning video not found")
    return learning_video_response(video.storage_key, video.content_type, request)


@router.patch("/videos/{video_id}", response_model=LearningVideoRead)
def update_video_metadata(
    video_id: int,
    payload: LearningVideoUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    video = db.query(LearningVideo).filter(LearningVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Learning video not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(video, key, value)
    video.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(video)
    return video


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    video = db.query(LearningVideo).filter(LearningVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Learning video not found")
    storage_key = video.storage_key
    db.delete(video)
    db.commit()
    delete_learning_video(storage_key)
