# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./corpus.db")

# SQLite a besoin de ce connect_args
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Dépendance FastAPI pour obtenir une session DB par requête
from typing import Generator
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
