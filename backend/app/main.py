# app/main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
from .api.endpoints import phrases
from .api.endpoints import enregistrements
from .api.endpoints import auth
from .api.endpoints import admin_data
from .api.router import api_router as speech_api_router
from .learning import routes as learning_routes

# AJOUTS pour les fichiers statiques et le bon MIME
from fastapi.staticfiles import StaticFiles
import mimetypes
from sqlalchemy import inspect, text
from .storage import LOCAL_AUDIO_DIR
from .auth import (
    BOOTSTRAP_ADMIN_DISPLAY_NAME,
    BOOTSTRAP_ADMIN_EMAIL,
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_CLASS_PASSWORD,
    BOOTSTRAP_CLASS_USERS,
    hash_password,
)
from .models.user import User
mimetypes.add_type('audio/webm', '.webm')

app = FastAPI(
    title="KeltiaWave API",
    description="Unified API for Record, Transcribe, Subtitles, Corpus and Learning.",
    version="1.0.0",
)

# Compatibilité des tables Corpus historiques. Les tables Learning sont gérées
# exclusivement par Alembic afin de garder des migrations versionnées.
corpus_tables = [
    table for table in Base.metadata.sorted_tables
    if not table.name.startswith("learning_")
]
Base.metadata.create_all(bind=engine, tables=corpus_tables)

def ensure_dev_columns() -> None:
    existing = {col["name"] for col in inspect(engine).get_columns("audios")}
    wanted = {
        "origin": "TEXT DEFAULT 'user' NOT NULL",
        "phrase_source": "TEXT",
        "domain": "TEXT",
        "speaker_region": "TEXT",
        "speaker_city": "TEXT",
        "speaker_accent": "TEXT",
        "speaker_level": "TEXT",
        "validated_by": "TEXT",
        "validator_role": "TEXT",
        "validation_weight": "TEXT",
        "validation_comment": "TEXT",
        "contributor_name": "TEXT",
        "contributor_email": "TEXT",
        "contributor_school": "TEXT",
        "contributor_school_level": "TEXT",
    }
    missing = [(name, ddl) for name, ddl in wanted.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, ddl in missing:
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE audios ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE audios ADD COLUMN {name} {ddl}"))

ensure_dev_columns()

def ensure_phrase_columns() -> None:
    existing = {col["name"] for col in inspect(engine).get_columns("phrases")}
    wanted = {
        "source": "TEXT",
        "traduction_fr": "TEXT",
    }
    missing = [(name, ddl) for name, ddl in wanted.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing:
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE phrases ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE phrases ADD COLUMN {name} {ddl}"))

ensure_phrase_columns()

def ensure_validation_columns() -> None:
    existing = {col["name"] for col in inspect(engine).get_columns("audio_validations")}
    wanted = {"comment": "TEXT", "pronunciation_level": "TEXT", "pronunciation_region": "TEXT"}
    with engine.begin() as conn:
        for name, ddl in wanted.items():
            if name in existing:
                continue
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE audio_validations ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE audio_validations ADD COLUMN {name} {ddl}"))

ensure_validation_columns()

def ensure_user_columns() -> None:
    existing = {col["name"] for col in inspect(engine).get_columns("users")}
    wanted = {
        "must_change_password": "BOOLEAN DEFAULT FALSE NOT NULL",
        "profile_type": "TEXT DEFAULT 'contributor' NOT NULL",
        "breton_level": "TEXT DEFAULT 'undefined' NOT NULL",
        "organization": "TEXT",
        "school": "TEXT",
        "school_level": "TEXT",
    }
    missing = [(name, ddl) for name, ddl in wanted.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, ddl in missing:
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            elif name == "must_change_password":
                conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL"))
            else:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users
            SET profile_type = CASE
                WHEN role = 'admin' THEN 'admin'
                WHEN role = 'teacher' THEN 'teacher'
                ELSE COALESCE(NULLIF(profile_type, ''), 'contributor')
            END,
            role = CASE
                WHEN role IN ('admin', 'teacher', 'contributor', 'learner') THEN role
                ELSE 'contributor'
            END,
            breton_level = CASE LOWER(COALESCE(NULLIF(breton_level, ''), language_level, 'undefined'))
                WHEN 'a1' THEN 'A1'
                WHEN 'a2' THEN 'A2'
                WHEN 'b1' THEN 'B1'
                WHEN 'b2' THEN 'B2'
                WHEN 'c1' THEN 'C1'
                WHEN 'c2' THEN 'C2'
                WHEN 'native' THEN 'native'
                WHEN 'native-heritage' THEN 'native'
                ELSE 'undefined'
            END,
            organization = COALESCE(NULLIF(organization, ''), NULLIF(affiliation, ''), school)
        """))

ensure_user_columns()

def bootstrap_admin_user() -> None:
    if not BOOTSTRAP_ADMIN_EMAIL or not BOOTSTRAP_ADMIN_PASSWORD:
        return

    from .db import SessionLocal

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == BOOTSTRAP_ADMIN_EMAIL).first()
        if existing:
            changed = False
            if existing.role != "admin":
                existing.role = "admin"
                changed = True
            if existing.profile_type != "admin":
                existing.profile_type = "admin"
                changed = True
            if existing.auth_status != "verified":
                existing.auth_status = "verified"
                changed = True
            if not existing.active:
                existing.active = True
                changed = True
            if changed:
                db.commit()
            return

        user = User(
            email=BOOTSTRAP_ADMIN_EMAIL,
            password_hash=hash_password(BOOTSTRAP_ADMIN_PASSWORD),
            display_name=BOOTSTRAP_ADMIN_DISPLAY_NAME or BOOTSTRAP_ADMIN_EMAIL,
            profile_type="admin",
            role="admin",
            auth_status="verified",
            must_change_password=True,
            active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

bootstrap_admin_user()

CLASS_TEST_USERS = [
    {
        "email": "tiar1@keltia.test",
        "display_name": "Mael Le Gall",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-1",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "a2",
    },
    {
        "email": "tiar2@keltia.test",
        "display_name": "Lenaig Kergoat",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-2",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b1",
    },
    {
        "email": "tiar3@keltia.test",
        "display_name": "Ti ar Vretonned 3",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-3",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b1",
    },
    {
        "email": "tiar4@keltia.test",
        "display_name": "Ti ar Vretonned 4",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-4",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b2",
    },
    {
        "email": "emsav1@keltia.test",
        "display_name": "Annaig Le Roux",
        "school": "skol-an-emsav",
        "school_level": "niveau-1",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "a2",
    },
    {
        "email": "emsav2@keltia.test",
        "display_name": "Youenn Kervella",
        "school": "skol-an-emsav",
        "school_level": "niveau-2",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b1",
    },
    {
        "email": "emsav3@keltia.test",
        "display_name": "Skol an Emsav 3",
        "school": "skol-an-emsav",
        "school_level": "niveau-3",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b1",
    },
    {
        "email": "emsav4@keltia.test",
        "display_name": "Skol an Emsav 4",
        "school": "skol-an-emsav",
        "school_level": "niveau-4",
        "role": "contributor",
        "auth_status": "identified",
        "language_level": "b2",
    },
    {
        "email": "prof.tiar1@keltia.test",
        "display_name": "Nolwenn Morvan",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-3",
        "role": "teacher",
        "auth_status": "verified",
        "language_level": "c1",
    },
    {
        "email": "prof.tiar2@keltia.test",
        "display_name": "Yann-Fanch Kervella",
        "school": "ti-ar-vretonned",
        "school_level": "niveau-4",
        "role": "teacher",
        "auth_status": "verified",
        "language_level": "c1",
    },
    {
        "email": "prof.emsav1@keltia.test",
        "display_name": "Soazig Ar Gall",
        "school": "skol-an-emsav",
        "school_level": "niveau-3",
        "role": "teacher",
        "auth_status": "verified",
        "language_level": "c1",
    },
    {
        "email": "prof.emsav2@keltia.test",
        "display_name": "Tangi Le Berre",
        "school": "skol-an-emsav",
        "school_level": "niveau-4",
        "role": "teacher",
        "auth_status": "verified",
        "language_level": "c1",
    },
]


def class_test_notes() -> str:
    return f"Compte de test classe. Mot de passe eleve : {BOOTSTRAP_CLASS_PASSWORD}"


def bootstrap_class_users() -> None:
    if not BOOTSTRAP_CLASS_USERS or len(BOOTSTRAP_CLASS_PASSWORD) < 8:
        return

    from .db import SessionLocal

    db = SessionLocal()
    try:
        test_admin_email = "learning.admin@keltia.test"
        test_admin = db.query(User).filter(User.email == test_admin_email).first()
        if not test_admin:
            db.add(User(
                email=test_admin_email,
                password_hash=hash_password(BOOTSTRAP_CLASS_PASSWORD),
                display_name="Admin Learning",
                profile_type="admin",
                role="admin",
                auth_status="verified",
                breton_level="C1",
                organization="KeltiaWave",
                notes=class_test_notes(),
                must_change_password=False,
                active=True,
            ))
        for item in CLASS_TEST_USERS:
            existing = db.query(User).filter(User.email == item["email"]).first()
            if existing:
                changed = False
                for key in ("display_name", "school", "school_level", "language_level"):
                    if getattr(existing, key) != item[key]:
                        setattr(existing, key, item[key])
                        changed = True
                profile_type = "teacher" if item["role"] == "teacher" else "student"
                role = "teacher" if item["role"] == "teacher" else "learner"
                breton_level = item["language_level"].upper()
                organization = item["school"]
                for key, value in (
                    ("profile_type", profile_type),
                    ("role", role),
                    ("breton_level", breton_level),
                    ("organization", organization),
                ):
                    if getattr(existing, key) != value:
                        setattr(existing, key, value)
                        changed = True
                if existing.notes != class_test_notes():
                    existing.notes = class_test_notes()
                    changed = True
                if existing.auth_status != item["auth_status"]:
                    existing.auth_status = item["auth_status"]
                    changed = True
                if not existing.active:
                    existing.active = True
                    changed = True
                if changed:
                    db.commit()
                continue

            db.add(User(
                email=item["email"],
                password_hash=hash_password(BOOTSTRAP_CLASS_PASSWORD),
                display_name=item["display_name"],
                profile_type="teacher" if item["role"] == "teacher" else "student",
                role="teacher" if item["role"] == "teacher" else "learner",
                auth_status=item["auth_status"],
                breton_level=item["language_level"].upper(),
                organization=item["school"],
                language_level=item["language_level"],
                school=item["school"],
                school_level=item["school_level"],
                affiliation=item["display_name"],
                notes=class_test_notes(),
                must_change_password=False,
                active=True,
            ))
        db.commit()
    finally:
        db.close()


bootstrap_class_users()

# Compat dev: expose les anciens fichiers locaux.
app.mount("/static/audios", StaticFiles(directory=str(LOCAL_AUDIO_DIR)), name="audios")

# CORS partagé par les cinq applications autonomes.
default_origins = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (4200, 4300, 4400, 4500, 4600)
]
configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API
app.include_router(phrases.router, prefix="/api/phrases", tags=["phrases"])
app.include_router(enregistrements.router, prefix="/api/audios", tags=["audios"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_data.router, prefix="/api/admin-data", tags=["admin-data"])
app.include_router(learning_routes.router, prefix="/api/learning", tags=["learning"])
app.include_router(speech_api_router)

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"name": "KeltiaWave API", "status": "ok"}
