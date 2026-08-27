# app/api/endpoints/phrases.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db import get_db
from ...models import Audio, Phrase
from ...schemas import PhraseCreate, PhraseUpdate, PhraseRead
from ...auth import get_current_user
from ...phrase_themes import classify_phrase_theme

router = APIRouter()

@router.get("/", response_model=List[PhraseRead])
def list_phrases(langue: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Phrase)
    if langue:
        query = query.filter(Phrase.langue == langue)
    return query.order_by(Phrase.id.desc()).all()

@router.post("/", response_model=PhraseRead, status_code=201)
def create_phrase(payload: PhraseCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher or admin role required")
    values = payload.model_dump()
    if not (values.get("theme") or "").strip():
        raise HTTPException(status_code=400, detail="Theme is required")
    if values.get("niveau") not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        raise HTTPException(status_code=400, detail="Level is required")
    obj = Phrase(**values)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{phrase_id}", response_model=PhraseRead)
def get_phrase(phrase_id: int, db: Session = Depends(get_db)):
    obj = db.get(Phrase, phrase_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Phrase not found")
    return obj

@router.patch("/{phrase_id}", response_model=PhraseRead)
def update_phrase(phrase_id: int, payload: PhraseUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    obj = db.get(Phrase, phrase_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Phrase not found")
    values = payload.model_dump(exclude_unset=True)
    if "theme" in values and not (values.get("theme") or "").strip():
        values["theme"] = classify_phrase_theme(values.get("texte") or obj.texte)
    for k, v in values.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{phrase_id}", status_code=204)
def delete_phrase(phrase_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    obj = db.get(Phrase, phrase_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Phrase not found")
    if db.query(Audio).filter(Audio.phrase_id == phrase_id).first():
        raise HTTPException(status_code=409, detail="Cette phrase possède des enregistrements et ne peut pas être supprimée")
    db.delete(obj)
    db.commit()
    return
