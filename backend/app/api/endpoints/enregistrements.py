# app/api/endpoints/enregistrements.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ...db import get_db
from ...auth import get_current_user, get_optional_user, validation_weight_for
from ...models.audio import Audio, AudioStatus, AudioValidation
from ...schemas.audio import AudioRead
from ...storage import audio_response, save_audio_upload

router = APIRouter()


# 1) Upload d’un fichier audio
@router.post("/", response_model=AudioRead, status_code=201)
async def upload_audio(
    phrase_id: int = Form(...),
    phrase_source: str | None = Form(None),
    domain: str | None = Form(None),
    speaker_region: str | None = Form(None),
    speaker_city: str | None = Form(None),
    speaker_accent: str | None = Form(None),
    speaker_level: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fichier manquant")

    storage_ref = await save_audio_upload(file, phrase_id)

    # Enregistrement DB
    audio = Audio(
        phrase_id=phrase_id,
        filename=storage_ref,
        origin="user",
        status=AudioStatus.pending,
        phrase_source=phrase_source,
        domain=domain,
        speaker_region=speaker_region,
        speaker_city=speaker_city,
        speaker_accent=speaker_accent,
        speaker_level=speaker_level,
        contributor_name=(current_user.display_name if current_user else None),
        contributor_email=(current_user.email if current_user else None),
        contributor_school=(current_user.organization if current_user else None),
        contributor_school_level=(current_user.school_level if current_user else None),
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


# 2) Lister les enregistrements par statut (default: pending)
@router.get("/", response_model=list[AudioRead])
def list_audios(
    status: AudioStatus = AudioStatus.pending,
    db: Session = Depends(get_db),
):
    return db.query(Audio).filter(Audio.status == status).all()


@router.get("/{audio_id}/file")
def get_audio_file(audio_id: int, db: Session = Depends(get_db)):
    audio = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio_response(audio.filename)


@router.patch("/{audio_id}", response_model=AudioRead)
def update_audio_metadata(
    audio_id: int,
    phrase_source: str | None = Form(None),
    domain: str | None = Form(None),
    speaker_region: str | None = Form(None),
    speaker_city: str | None = Form(None),
    speaker_accent: str | None = Form(None),
    speaker_level: str | None = Form(None),
    db: Session = Depends(get_db),
):
    audio = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")

    audio.phrase_source = phrase_source or None
    audio.domain = domain or None
    audio.speaker_region = speaker_region or None
    audio.speaker_city = speaker_city or None
    audio.speaker_accent = speaker_accent or None
    audio.speaker_level = speaker_level or None
    db.commit()
    db.refresh(audio)
    return audio


# 3) Valider / rejeter un enregistrement
@router.post("/{audio_id}/validate", response_model=AudioRead)
def validate_audio(
    audio_id: int,
    approved: bool = Form(...),
    validator: str | None = Form(None),
    validator_role: str | None = Form(None),
    validation_weight: str | None = Form(None),
    pronunciation_level: str | None = Form(None),
    pronunciation_region: str | None = Form(None),
    comment: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    audio = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio introuvable")

    if current_user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher or admin role required")
    allowed_levels = {"A1", "A2", "B1", "B2", "C1", "C2", "native"}
    if approved and pronunciation_level not in allowed_levels:
        raise HTTPException(status_code=400, detail="Pronunciation level is required")
    cleaned_region = (pronunciation_region or "").strip()
    if approved and not cleaned_region:
        raise HTTPException(status_code=400, detail="Pronunciation region is required")
    validator_name = current_user.display_name or current_user.email
    role = current_user.role
    weight = str(validation_weight_for(current_user))

    audio.status = AudioStatus.approved if approved else AudioStatus.rejected
    audio.validated_at = func.now()
    audio.validated_by = validator_name
    audio.validator_role = role
    audio.validation_weight = weight
    audio.validation_comment = comment or None
    db.add(AudioValidation(
        audio_id=audio.id,
        decision="approved" if approved else "rejected",
        validator=validator_name,
        validator_role=role,
        validation_weight=weight,
        pronunciation_level=pronunciation_level if approved else None,
        pronunciation_region=cleaned_region if approved else None,
        comment=comment or None,
    ))
    db.commit()
    db.refresh(audio)
    return audio


@router.post("/{audio_id}/comment", response_model=AudioRead)
def comment_audio(
    audio_id: int,
    comment: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if current_user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher or admin role required")

    cleaned_comment = comment.strip()
    if not cleaned_comment:
        raise HTTPException(status_code=400, detail="Commentaire requis")

    audio = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio introuvable")

    validator_name = current_user.display_name or current_user.email
    weight = str(validation_weight_for(current_user))
    audio.validation_comment = cleaned_comment
    existing_validation = (
        db.query(AudioValidation)
        .filter(
            AudioValidation.audio_id == audio.id,
            AudioValidation.validator == validator_name,
            AudioValidation.validator_role == current_user.role,
        )
        .order_by(AudioValidation.created_at.desc(), AudioValidation.id.desc())
        .first()
    )
    if existing_validation:
        existing_validation.comment = cleaned_comment
    else:
        db.add(AudioValidation(
            audio_id=audio.id,
            decision="commented",
            validator=validator_name,
            validator_role=current_user.role,
            validation_weight=weight,
            comment=cleaned_comment,
        ))
    db.commit()
    db.refresh(audio)
    return audio
