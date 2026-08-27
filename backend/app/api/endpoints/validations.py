# backend/app/api/endpoints/validations.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db import get_db
from app import crud

# Chemins « propres » en anglais
router = APIRouter(prefix="/api/validations", tags=["validations"])

@router.get("/")
def list_audios_for_validation(
    status: Optional[str] = Query("pending", pattern="^(pending|approved|rejected)$"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    total, items = crud.list_audios(db, status=status, skip=skip, limit=limit)
    return {"total": total, "items": items}

@router.patch("/{audio_id}")
def decide_audio_validation(
    audio_id: int,
    status: str,
    comment: Optional[str] = None,
    validator: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if status not in ("approved", "rejected"):
        raise HTTPException(400, detail="status must be approved|rejected")

    audio = crud.update_audio_status(
        db, audio_id=audio_id, status=status, validator=validator, comment=comment
    )
    if not audio:
        raise HTTPException(404, detail="Audio not found")

    # On renvoie un petit résumé standard
    return {
        "id": audio.id,
        "status": audio.status,
        "validator": getattr(audio, "validator", None),
        "comment": getattr(audio, "validator_comment", None),
    }
