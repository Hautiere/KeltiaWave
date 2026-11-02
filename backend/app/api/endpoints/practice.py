"""Authenticated private audio hand-in and teacher/admin feedback."""
from datetime import datetime
import secrets
from pathlib import Path
from uuid import uuid4
from ... import storage
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...auth import get_current_user
from ...db import get_db
from ...models.user import User
from ...models.practice import PracticeClass, PracticeMembership, PracticeSubmission
from ...storage import audio_response

router = APIRouter()
MAX_AUDIO = 50 * 1024 * 1024


def class_payload(cls):
    return {'id': cls.id, 'name': cls.name, 'code': cls.code}


def may_review(user, row, db):
    if user.role == 'admin':
        return True
    cls = db.get(PracticeClass, row.class_id) if row.class_id else None
    return user.role == 'teacher' and cls is not None and cls.teacher_id == user.id


def payload(row, db):
    owner = db.get(User, row.user_id)
    reviewer = db.get(User, row.reviewer_id) if row.reviewer_id else None
    cls = db.get(PracticeClass, row.class_id) if row.class_id else None
    return dict(id=row.id, title=row.title, transcript=row.transcript, status=row.status,
                feedback=row.feedback, created_at=row.created_at, reviewed_at=row.reviewed_at,
                author=owner.display_name if owner else 'Compte supprimé',
                reviewer=reviewer.display_name if reviewer else None,
                destination=cls.name if cls else 'Administration')


@router.get('/classes')
def classes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.get(PracticeMembership, user.id)
    joined = db.get(PracticeClass, membership.class_id) if membership else None
    owned = db.query(PracticeClass).filter(PracticeClass.teacher_id == user.id).all()
    return {'joined': class_payload(joined) if joined else None, 'owned': [class_payload(c) for c in owned]}


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.post('/classes', status_code=201)
def create_class(body: ClassCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {'teacher', 'admin'}:
        raise HTTPException(403, 'Teacher or admin role required')
    name = body.name.strip()
    if not name:
        raise HTTPException(400, 'Nom de classe requis')
    cls = PracticeClass(name=name, code=secrets.token_hex(6).upper(), teacher_id=user.id)
    db.add(cls); db.commit(); db.refresh(cls)
    return class_payload(cls)


class JoinClass(BaseModel):
    code: str = Field(min_length=1, max_length=32)


@router.post('/classes/join')
def join_class(body: JoinClass, user=Depends(get_current_user), db: Session = Depends(get_db)):
    cls = db.query(PracticeClass).filter(PracticeClass.code == body.code.strip().upper()).first()
    if not cls:
        raise HTTPException(404, 'Code de classe inconnu')
    teacher = db.get(User, cls.teacher_id)
    if not teacher or not teacher.active or teacher.role not in {'teacher', 'admin'}:
        raise HTTPException(409, 'Classe indisponible')
    membership = db.get(PracticeMembership, user.id)
    if membership:
        membership.class_id = cls.id
    else:
        db.add(PracticeMembership(user_id=user.id, class_id=cls.id))
    db.commit()
    return class_payload(cls)


@router.delete('/classes/join', status_code=204)
def leave_class(user=Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.get(PracticeMembership, user.id)
    if membership:
        db.delete(membership); db.commit()


@router.get('/submissions')
def list_submissions(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(PracticeSubmission).filter(PracticeSubmission.user_id == user.id).order_by(PracticeSubmission.id.desc()).all()
    return [payload(r, db) for r in rows]


@router.post('/submissions', status_code=201)
async def submit(title: str = Form(..., min_length=1, max_length=160),
                 transcript: str = Form('', max_length=50000), file: UploadFile = File(...),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not title.strip():
        raise HTTPException(400, 'Titre requis')
    if not file.filename or not (file.content_type or '').startswith('audio/'):
        raise HTTPException(400, 'Fichier audio requis')
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_AUDIO:
            raise HTTPException(413, 'Audio limité à 50 Mo')
    if size == 0:
        raise HTTPException(400, 'Audio vide')
    await file.seek(0)
    membership = db.get(PracticeMembership, user.id)
    cls = db.get(PracticeClass, membership.class_id) if membership else None
    teacher = db.get(User, cls.teacher_id) if cls else None
    class_id = cls.id if cls and teacher and teacher.active and teacher.role in {'teacher', 'admin'} else None
    # Keep private work outside the publicly mounted corpus audio directory.
    ext = storage._safe_ext(file.filename)
    key = f'practice/{uuid4().hex}{ext}'
    if storage.s3_enabled():
        bucket = storage._s3_bucket()
        storage._s3_client().upload_fileobj(file.file, bucket, key, ExtraArgs={'ContentType': file.content_type})
        ref = f's3://{bucket}/{key}'
    else:
        directory = storage.LOCAL_AUDIO_DIR.parent / 'practice'
        directory.mkdir(parents=True, exist_ok=True)
        dest = directory / Path(key).name
        dest.write_bytes(await file.read())
        ref = str(dest.resolve())
    row = PracticeSubmission(user_id=user.id, class_id=class_id, title=title.strip(), transcript=transcript, filename=ref)
    db.add(row); db.commit(); db.refresh(row)
    return payload(row, db)


@router.get('/reviews')
def review_queue(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {'teacher', 'admin'}:
        raise HTTPException(403, 'Teacher or admin role required')
    query = db.query(PracticeSubmission)
    if user.role != 'admin':
        query = query.join(PracticeClass, PracticeSubmission.class_id == PracticeClass.id).filter(PracticeClass.teacher_id == user.id)
    return [payload(r, db) for r in query.order_by(PracticeSubmission.id.desc()).all()]


@router.get('/submissions/{submission_id}/file')
def listen(submission_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PracticeSubmission, submission_id)
    if not row or (row.user_id != user.id and not may_review(user, row, db)):
        raise HTTPException(404, 'Audio introuvable')
    response = audio_response(row.filename)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


class Review(BaseModel):
    status: str = Field(pattern='^(approved|changes_requested)$')
    feedback: str = Field(min_length=1, max_length=5000)


@router.post('/submissions/{submission_id}/review')
def review(submission_id: int, body: Review, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PracticeSubmission, submission_id)
    if not row or not may_review(user, row, db):
        raise HTTPException(404, 'Audio introuvable')
    if not body.feedback.strip():
        raise HTTPException(400, 'Retour requis')
    row.status = body.status; row.feedback = body.feedback.strip()
    row.reviewer_id = user.id; row.reviewed_at = datetime.utcnow()
    db.commit(); db.refresh(row)
    return payload(row, db)
