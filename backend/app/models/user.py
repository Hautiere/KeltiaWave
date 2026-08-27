from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from ..db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    profile_type = Column(String, default="contributor", nullable=False)
    role = Column(String, default="contributor", nullable=False)
    auth_status = Column(String, default="identified", nullable=False)
    breton_level = Column(String, default="undefined", nullable=False)
    organization = Column(String, nullable=True)
    # Legacy columns kept during the transition for historical local databases.
    language_level = Column(String, nullable=True)
    school = Column(String, nullable=True)
    school_level = Column(String, nullable=True)
    affiliation = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
