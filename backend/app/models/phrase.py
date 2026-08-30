# app/models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..db import Base

class Phrase(Base):
    __tablename__ = "phrases"

    id = Column(Integer, primary_key=True, index=True)
    texte = Column(String, nullable=False)
    traduction_fr = Column(String, nullable=True)
    theme = Column(String, nullable=True)     # ex: "général"
    niveau = Column(String, nullable=True)    # ex: "A1"
    source = Column(String, nullable=True)    # ex: "livre", "dictionnaire", "archive-dastum"
    source_url = Column(String, nullable=True)
    langue = Column(String, nullable=True)    # ex: "br"
    auteur = Column(String, nullable=True)    # (optionnel)
    url_audio = Column(String, nullable=True) # sera rempli quand S3 sera branché
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
