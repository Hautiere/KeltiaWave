# backend/app/crud.py
from __future__ import annotations
from typing import Optional, Tuple, List
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

# ---- Imports modèles : tolérants (Enum facultatif) --------------------------
try:
    from app.models.audio import Audio, AudioStatus  # si tu as un Enum
    HAS_ENUM = True
except Exception:
    from app.models.audio import Audio               # fallback si pas d'Enum
    HAS_ENUM = False

# Si tu as un modèle Phrase (requis pour phrase_id FK), on l'importe proprement
try:
    from app.models.phrase import Phrase  # optionnel, juste pour vérifs
except Exception:
    Phrase = None  # type: ignore

# ---------------------------------------------------------------------------

def list_audios(db: Session, status: Optional[str], skip: int, limit: int) -> Tuple[int, List[Audio]]:
    """
    Liste paginée d'audios, filtrable par status ('pending'|'approved'|'rejected').
    Retourne (total, items).
    """
    q = db.query(Audio)
    if status:
        if HAS_ENUM:
            q = q.filter(Audio.status == AudioStatus(status))
        else:
            q = q.filter(Audio.status == status)
    total = q.count()
    items = q.order_by(Audio.id.asc()).offset(skip).limit(limit).all()
    return total, items


def update_audio_status(
    db: Session,
    audio_id: int,
    status: str,
    validator: Optional[str] = None,
    comment: Optional[str] = None,
) -> Optional[Audio]:
    """
    Met à jour le statut d'un enregistrement et optionnellement le valideur / commentaire.
    N'échoue pas si les colonnes 'validator'/'validator_comment' n'existent pas.
    """
    audio: Optional[Audio] = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        return None

    # status (Enum ou string)
    if HAS_ENUM:
        try:
            audio.status = AudioStatus(status)
        except Exception:
            audio.status = status  # au cas où
    else:
        audio.status = status

    # champs optionnels (selon ton modèle)
    if validator is not None and hasattr(audio, "validator"):
        setattr(audio, "validator", validator)
    if hasattr(audio, "validator_comment"):
        setattr(audio, "validator_comment", comment)

    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


# === Upload côté "enregistrements" (contributeur) ===========================

def create_audio(db: Session, phrase_id: int, file) -> Audio:
    """
    Crée un Audio en stockant le fichier sur disque (MVP).
    - Dépendances minimales : table Audio avec colonnes (id, phrase_id, filepath, status?)
    - Si tu as un Enum AudioStatus, le status initial sera 'pending' automatiquement par défaut modèle.
    """
    # Vérif (facultative) : la phrase existe ?
    if Phrase is not None:
        exists = db.query(Phrase).filter(Phrase.id == phrase_id).first()
        if not exists:
            raise ValueError(f"Phrase {phrase_id} not found")

    # Dossier de stockage: backend/data/audios/
    base_dir = (Path(__file__).resolve().parents[1].parent / "data" / "audios")
    base_dir.mkdir(parents=True, exist_ok=True)

    # Génère un nom de fichier unique
    ext = _safe_ext(getattr(file, "filename", None))
    filename = f"{uuid4().hex}{ext}"
    abs_path = base_dir / filename

    # Lecture "synchrone" du UploadFile (compatible FastAPI)
    # - UploadFile a .file (SpooledTemporaryFile) ⇒ lecture sync
    raw = file.file.read() if hasattr(file, "file") else file.read()
    abs_path.write_bytes(raw)

    # Chemin relatif enregistré en DB (ex: "data/audios/xxxx.webm")
    rel_path = str(Path("data") / "audios" / filename)

    # Instancie le modèle
    audio = Audio(
        phrase_id=phrase_id,
        filepath=rel_path,
        # si ton modèle a 'status' avec default='pending', inutile de renseigner
        **(_status_pending_kw() if hasattr(Audio, "status") else {})
    )

    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


# === Helpers =================================================================

def _safe_ext(name: Optional[str]) -> str:
    """Retourne une extension sécurisée à partir d'un nom de fichier (par défaut .webm)."""
    if not name or "." not in name:
        return ".webm"
    ext = name.rsplit(".", 1)[-1].lower()
    # Liste blanche simple
    if ext not in {"webm", "wav", "mp3", "m4a", "ogg"}:
        return ".webm"
    return f".{ext}"


def _status_pending_kw() -> dict:
    """Construit un dict pour initialiser status='pending' selon que tu as un Enum ou non."""
    if not hasattr(Audio, "status"):
        return {}
    if HAS_ENUM:
        return {"status": AudioStatus("pending")}
    return {"status": "pending"}
