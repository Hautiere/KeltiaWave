from collections import Counter
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ...auth import require_admin, validation_weight_for
from ...db import get_db
from ...models.audio import Audio, AudioStatus, AudioValidation
from ...models.phrase import Phrase
from ...models.user import User
from ...storage import delete_audio_file, storage_backend_info, storage_ref_exists
from scripts.export_corpus_dataset import EXPORT_FIELDS, audio_row, copy_storage_ref
from scripts.import_corpus_dataset import import_dataset

router = APIRouter()


class SegmentUpdate(BaseModel):
    texte: str | None = None
    traduction_fr: str | None = None
    source: str | None = None
    source_url: str | None = None
    domain: str | None = None
    level: str | None = None
    speaker_region: str | None = None
    speaker_city: str | None = None
    speaker_accent: str | None = None
    speaker_level: str | None = None
    contributor_name: str | None = None
    status: AudioStatus | None = None


class DatasetCleanRequest(BaseModel):
    dry_run: bool = True
    remove_phrases_without_audio: bool = True
    remove_missing_storage_audios: bool = False
    include_legacy_imports: bool = False


class DatasetClearRequest(BaseModel):
    dry_run: bool = True
    delete_phrases_without_audio: bool = True
    include_user_data: bool = False
    include_legacy_imports: bool = False


def dataset_name(phrase: Phrase, audio: Audio | None = None) -> str:
    return (phrase.source or (audio.phrase_source if audio else None) or "sans-source").strip()


def audio_has_user_metadata(audio: Audio) -> bool:
    return any([
        audio.contributor_name,
        audio.contributor_email,
        audio.contributor_school,
        audio.contributor_school_level,
    ])


def is_dataset_owned_audio(audio: Audio, include_legacy_imports: bool = False) -> bool:
    if audio.origin == "dataset":
        return True
    return include_legacy_imports and audio.origin in (None, "", "user") and not audio_has_user_metadata(audio)


def audio_matches_dataset(phrase: Phrase, audio: Audio, name: str) -> bool:
    return dataset_name(phrase, audio) == name or phrase.source == name or audio.phrase_source == name


def extract_zip_safely(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise HTTPException(status_code=400, detail="Unsafe path in ZIP archive")
        archive.extractall(destination)


def segment_payload(audio: Audio, phrase: Phrase | None) -> dict:
    return {
        "id": audio.id,
        "phrase_id": phrase.id if phrase else audio.phrase_id,
        "texte": phrase.texte if phrase else "Enregistrement sans texte associé",
        "traduction_fr": phrase.traduction_fr if phrase else None,
        "dataset": dataset_name(phrase, audio) if phrase else (audio.phrase_source or "sans-source"),
        "source": phrase.source if phrase else audio.phrase_source,
        "source_url": phrase.source_url if phrase else None,
        "domain": audio.domain or (phrase.theme if phrase else None),
        "level": phrase.niveau if phrase else None,
        "speaker_region": audio.speaker_region,
        "speaker_city": audio.speaker_city,
        "speaker_accent": audio.speaker_accent,
        "speaker_level": audio.speaker_level,
        "status": audio.status.value,
        "origin": audio.origin,
        "filename": audio.filename,
        "audio_url": f"/api/audios/{audio.id}/file",
        "created_at": audio.created_at,
        "validated_at": audio.validated_at,
        "validated_by": audio.validated_by,
        "contributor_name": audio.contributor_name,
    }


@router.get("/overview")
def overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phrases = db.query(Phrase).all()
    audios = db.query(Audio).all()
    phrase_ids = {phrase.id for phrase in phrases}
    audio_phrase_ids = {audio.phrase_id for audio in audios}
    return {
        "datasets": len({dataset_name(phrase) for phrase in phrases}),
        "phrases": len(phrases),
        "audios": len(audios),
        "approved": sum(audio.status == AudioStatus.approved for audio in audios),
        "pending": sum(audio.status == AudioStatus.pending for audio in audios),
        "rejected": sum(audio.status == AudioStatus.rejected for audio in audios),
        "phrases_without_audio": len(phrase_ids - audio_phrase_ids),
        "audios_without_text": len([audio for audio in audios if audio.phrase_id not in phrase_ids]),
    }


@router.get("/storage")
def storage(
    _: User = Depends(require_admin),
):
    return storage_backend_info()


@router.get("/datasets")
def list_datasets(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phrases = db.query(Phrase).all()
    audios = db.query(Audio).all()
    audios_by_phrase: dict[int, list[Audio]] = {}
    for audio in audios:
        audios_by_phrase.setdefault(audio.phrase_id, []).append(audio)

    rows: dict[str, dict] = {}
    for phrase in phrases:
        name = dataset_name(phrase)
        row = rows.setdefault(name, {
            "name": name,
            "phrases": 0,
            "audios": 0,
            "dataset_audios": 0,
            "user_audios": 0,
            "approved": 0,
            "pending": 0,
            "rejected": 0,
            "created_at": phrase.created_at,
        })
        row["phrases"] += 1
        row["created_at"] = min(row["created_at"], phrase.created_at)
        for audio in audios_by_phrase.get(phrase.id, []):
            row["audios"] += 1
            if audio.origin == "dataset":
                row["dataset_audios"] += 1
            else:
                row["user_audios"] += 1
            row[audio.status.value] += 1

    return sorted(rows.values(), key=lambda row: row["name"].lower())


@router.get("/datasets/{name}/export")
def export_dataset(
    name: str,
    background_tasks: BackgroundTasks,
    export_format: str = Query("csv", pattern="^(csv|json)$"),
    status_filter: str = Query("", alias="status"),
    include_user_data: bool = False,
    skip_missing: bool = True,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        audio_status = AudioStatus(status_filter) if status_filter else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid audio status") from exc

    temp_dir = Path(tempfile.mkdtemp(prefix=f"dataset-{name}-"))
    export_dir = temp_dir / "export"
    audio_dir = export_dir / "audios"
    audio_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    missing = []

    pairs = (
        db.query(Audio, Phrase)
        .join(Phrase, Phrase.id == Audio.phrase_id)
        .order_by(Audio.created_at.desc(), Audio.id.desc())
        .all()
    )
    for audio, phrase in pairs:
        if not audio_matches_dataset(phrase, audio, name):
            continue
        if audio_status and audio.status != audio_status:
            continue
        if not include_user_data and audio.origin != "dataset":
            continue

        ext = Path(audio.filename.split("?", 1)[0]).suffix.lower()
        if ext not in {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4"}:
            ext = ".webm"
        exported_name = f"audio-{audio.id}{ext}"
        exported_path = audio_dir / exported_name
        if not copy_storage_ref(audio.filename, exported_path):
            missing.append(audio.id)
            if not skip_missing:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise HTTPException(status_code=404, detail=f"Audio file missing for audio_id={audio.id}")
            continue
        rows.append(audio_row(audio, phrase, str(Path("audios") / exported_name)))

    if export_format == "json":
        metadata_path = export_dir / "metadata.json"
        metadata_path.write_text(json.dumps({"items": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        metadata_path = export_dir / "metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    manifest_path = export_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "dataset": name,
            "format": export_format,
            "exported_at": datetime.utcnow().isoformat(),
            "audios": len(rows),
            "missing_audio_ids": missing,
            "include_user_data": include_user_data,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    zip_path = temp_dir / f"{name}-dataset.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in export_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(export_dir))

    background_tasks.add_task(shutil.rmtree, temp_dir, True)
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")


@router.post("/datasets/import")
async def import_dataset_upload(
    metadata: UploadFile = File(...),
    audio_archive: UploadFile | None = File(None),
    name: str = Form("dataset"),
    audio_root: str = Form("audios"),
    langue: str = Form("br"),
    author: str = Form("import-corpus"),
    source: str = Form("import"),
    initial_status: AudioStatus = Form(AudioStatus.pending),
    _: User = Depends(require_admin),
):
    if not metadata.filename or Path(metadata.filename).suffix.lower() not in {".csv", ".json"}:
        raise HTTPException(status_code=400, detail="Metadata file must be CSV or JSON")

    temp_dir = Path(tempfile.mkdtemp(prefix="dataset-import-"))
    try:
        metadata_path = temp_dir / Path(metadata.filename).name
        metadata_path.write_bytes(await metadata.read())

        if audio_archive:
            if not audio_archive.filename or Path(audio_archive.filename).suffix.lower() != ".zip":
                raise HTTPException(status_code=400, detail="Audio archive must be a ZIP file")
            archive_path = temp_dir / "audios.zip"
            archive_path.write_bytes(await audio_archive.read())
            extract_zip_safely(archive_path, temp_dir)

        stats = import_dataset(argparse.Namespace(
            dataset=str(metadata_path),
            name=name,
            audio_root=str((temp_dir / audio_root).resolve()) if audio_root else None,
            langue=langue,
            author=author,
            source=source,
            status=initial_status.value,
        ))
        return {"dataset": name, "stats": stats}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/datasets/{name}/clean")
def clean_dataset(
    name: str,
    payload: DatasetCleanRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phrases = db.query(Phrase).filter(Phrase.source == name).all()
    audios = (
        db.query(Audio, Phrase)
        .join(Phrase, Phrase.id == Audio.phrase_id)
        .all()
    )
    phrase_ids_with_audio = {audio.phrase_id for audio, _ in audios}
    phrase_ids_to_delete = [
        phrase.id for phrase in phrases
        if payload.remove_phrases_without_audio and phrase.id not in phrase_ids_with_audio
    ]
    missing_audio_ids = []
    for audio, phrase in audios:
        if not audio_matches_dataset(phrase, audio, name):
            continue
        if not is_dataset_owned_audio(audio, payload.include_legacy_imports):
            continue
        if payload.remove_missing_storage_audios and not storage_ref_exists(audio.filename):
            missing_audio_ids.append(audio.id)

    if not payload.dry_run:
        if missing_audio_ids:
            for audio in db.query(Audio).filter(Audio.id.in_(missing_audio_ids)).all():
                db.delete(audio)
        if phrase_ids_to_delete:
            for phrase in db.query(Phrase).filter(Phrase.id.in_(phrase_ids_to_delete)).all():
                db.delete(phrase)
        db.commit()

    return {
        "dataset": name,
        "dry_run": payload.dry_run,
        "phrase_ids_without_audio": phrase_ids_to_delete,
        "missing_storage_audio_ids": missing_audio_ids,
        "deleted_phrases": 0 if payload.dry_run else len(phrase_ids_to_delete),
        "deleted_audios": 0 if payload.dry_run else len(missing_audio_ids),
    }


@router.post("/datasets/{name}/clear")
def clear_dataset(
    name: str,
    payload: DatasetClearRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    pairs = (
        db.query(Audio, Phrase)
        .join(Phrase, Phrase.id == Audio.phrase_id)
        .all()
    )
    audio_ids_to_delete = []
    protected_audio_ids = []
    phrase_ids_seen = set()
    for audio, phrase in pairs:
        if not audio_matches_dataset(phrase, audio, name):
            continue
        phrase_ids_seen.add(phrase.id)
        can_delete = payload.include_user_data or is_dataset_owned_audio(audio, payload.include_legacy_imports)
        if can_delete:
            audio_ids_to_delete.append(audio.id)
        else:
            protected_audio_ids.append(audio.id)

    phrases_to_delete = []
    if payload.delete_phrases_without_audio:
        for phrase in db.query(Phrase).filter(Phrase.source == name).all():
            remaining = db.query(Audio).filter(Audio.phrase_id == phrase.id).all()
            remaining_after_clear = [
                audio for audio in remaining
                if audio.id not in audio_ids_to_delete
            ]
            if not remaining_after_clear:
                phrases_to_delete.append(phrase.id)

    if not payload.dry_run:
        for audio in db.query(Audio).filter(Audio.id.in_(audio_ids_to_delete)).all():
            try:
                delete_audio_file(audio.filename)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Unable to delete stored audio {audio.id}: {exc}") from exc
            db.delete(audio)
        db.flush()
        if phrases_to_delete:
            for phrase in db.query(Phrase).filter(Phrase.id.in_(phrases_to_delete)).all():
                db.delete(phrase)
        db.commit()

    return {
        "dataset": name,
        "dry_run": payload.dry_run,
        "audio_ids_to_delete": audio_ids_to_delete,
        "protected_user_audio_ids": protected_audio_ids,
        "phrase_ids_to_delete": phrases_to_delete,
        "deleted_audios": 0 if payload.dry_run else len(audio_ids_to_delete),
        "deleted_phrases": 0 if payload.dry_run else len(phrases_to_delete),
    }


@router.get("/segments")
def list_segments(
    query: str = "",
    dataset: str = "",
    status_filter: str = Query("", alias="status"),
    limit: int = Query(250, ge=1, le=1000),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        audio_status = AudioStatus(status_filter) if status_filter else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid audio status") from exc

    pairs = (
        db.query(Audio, Phrase)
        .outerjoin(Phrase, Phrase.id == Audio.phrase_id)
        .order_by(Audio.created_at.desc(), Audio.id.desc())
        .all()
    )
    needle = query.strip().lower()
    result = []
    for audio, phrase in pairs:
        if audio_status and audio.status != audio_status:
            continue
        row_dataset = dataset_name(phrase, audio) if phrase else (audio.phrase_source or "sans-source")
        if dataset and row_dataset != dataset:
            continue
        if needle and needle not in " ".join([
            phrase.texte if phrase else "Enregistrement sans texte associé",
            (phrase.traduction_fr or "") if phrase else "",
            (phrase.source or "") if phrase else "",
            audio.domain or "",
            audio.filename,
        ]).lower():
            continue
        result.append(segment_payload(audio, phrase))
        if len(result) >= limit:
            break
    return result


@router.patch("/segments/{audio_id}")
def update_segment(
    audio_id: int,
    payload: SegmentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    audio = db.query(Audio).options(joinedload(Audio.validations)).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    phrase = db.get(Phrase, audio.phrase_id)
    patch = payload.model_dump(exclude_unset=True)

    if "texte" in patch:
        text = (patch["texte"] or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        phrase.texte = text
    if "traduction_fr" in patch:
        phrase.traduction_fr = (patch["traduction_fr"] or "").strip() or None
    if "source" in patch:
        phrase.source = (patch["source"] or "").strip() or None
    if "source_url" in patch:
        phrase.source_url = (patch["source_url"] or "").strip() or None
    if "domain" in patch:
        domain = (patch["domain"] or "").strip() or None
        audio.domain = domain
        phrase.theme = domain
    if "level" in patch:
        phrase.niveau = (patch["level"] or "").strip() or None
    for field in ("speaker_region", "speaker_city", "speaker_accent", "speaker_level", "contributor_name"):
        if field in patch:
            setattr(audio, field, (patch[field] or "").strip() or None)
    if "status" in patch:
        audio.status = patch["status"]
        decision = patch["status"].value
        if decision in {"approved", "rejected"}:
            validator_name = current_user.display_name or current_user.email
            audio.validated_at = datetime.utcnow()
            audio.validated_by = validator_name
            audio.validator_role = current_user.role
            audio.validation_weight = str(validation_weight_for(current_user))
            validation = (
                db.query(AudioValidation)
                .filter(AudioValidation.audio_id == audio.id, AudioValidation.validator == validator_name)
                .order_by(AudioValidation.id.desc())
                .first()
            )
            if validation:
                validation.decision = decision
                validation.pronunciation_level = audio.speaker_level if decision == "approved" else None
                validation.pronunciation_region = audio.speaker_region if decision == "approved" else None
                validation.created_at = audio.validated_at
            else:
                db.add(AudioValidation(
                    audio_id=audio.id,
                    decision=decision,
                    validator=validator_name,
                    validator_role=current_user.role,
                    validation_weight=audio.validation_weight,
                    pronunciation_level=audio.speaker_level if decision == "approved" else None,
                    pronunciation_region=audio.speaker_region if decision == "approved" else None,
                    created_at=audio.validated_at,
                ))

    db.commit()
    db.refresh(audio)
    return segment_payload(audio, phrase)


@router.delete("/segments/{audio_id}/audio", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment_audio(
    audio_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    audio = db.query(Audio).filter(Audio.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    try:
        delete_audio_file(audio.filename)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to delete stored audio: {exc}") from exc
    db.delete(audio)
    db.commit()


@router.get("/quality")
def quality_report(
    check_storage: bool = False,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phrases = db.query(Phrase).all()
    audios = db.query(Audio).all()
    phrase_ids = {phrase.id for phrase in phrases}
    audio_phrase_ids = {audio.phrase_id for audio in audios}
    normalized_texts = Counter(phrase.texte.strip().lower() for phrase in phrases if phrase.texte.strip())
    duplicate_texts = sorted(text for text, count in normalized_texts.items() if count > 1)
    missing_storage = []
    if check_storage:
        missing_storage = [audio.id for audio in audios if not storage_ref_exists(audio.filename)]

    return {
        "generated_at": datetime.utcnow(),
        "phrases_without_audio": [
            {"id": phrase.id, "texte": phrase.texte, "source": phrase.source}
            for phrase in phrases
            if phrase.id not in audio_phrase_ids
        ],
        "empty_text_phrase_ids": [phrase.id for phrase in phrases if not phrase.texte.strip()],
        "audios_without_text": [
            {"id": audio.id, "phrase_id": audio.phrase_id, "filename": audio.filename}
            for audio in audios
            if audio.phrase_id not in phrase_ids
        ],
        "duplicate_texts": duplicate_texts,
        "missing_storage_audio_ids": missing_storage,
        "storage_checked": check_storage,
    }
