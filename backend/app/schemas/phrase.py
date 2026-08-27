from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Champs communs (sans id/created_at)
class PhraseBase(BaseModel):
    texte: str = Field(..., min_length=1)
    traduction_fr: Optional[str] = None
    theme: Optional[str] = None
    niveau: Optional[str] = None   # ex: "A1", "B2", etc.
    source: Optional[str] = None
    langue: Optional[str] = None   # ex: "br"
    auteur: Optional[str] = None
    url_audio: Optional[str] = None

# Pour création (POST) – identique à Base
class PhraseCreate(PhraseBase):
    pass

# Pour mise à jour partielle (PATCH)
class PhraseUpdate(BaseModel):
    texte: Optional[str] = None
    traduction_fr: Optional[str] = None
    theme: Optional[str] = None
    niveau: Optional[str] = None
    source: Optional[str] = None
    langue: Optional[str] = None
    auteur: Optional[str] = None
    url_audio: Optional[str] = None

# Pour lecture/retour API (GET)
class PhraseRead(PhraseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 : permet de créer depuis un objet SQLAlchemy
