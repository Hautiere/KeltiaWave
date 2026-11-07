"""Private classroom submissions, independent of the public voice catalogue."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from ..db import Base


class PracticeClass(Base):
    __tablename__ = 'practice_classes'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    school = Column(String(160), nullable=False, default='')
    code = Column(String(32), unique=True, nullable=False)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False)


class PracticeMembership(Base):
    __tablename__ = 'practice_memberships'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    class_id = Column(Integer, ForeignKey('practice_classes.id'), nullable=False)


class PracticeSubmission(Base):
    __tablename__ = 'practice_submissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey('practice_classes.id'), nullable=True)
    title = Column(String(160), nullable=False)
    transcript = Column(Text, nullable=False, default='')
    filename = Column(String, nullable=False)
    status = Column(String(24), nullable=False, default='pending')
    feedback = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    feedback_revision = Column(Integer, nullable=False, default=0)
    feedback_seen_revision = Column(Integer, nullable=False, default=0)


class PracticeWebClassImport(Base):
    """Track imported web profile groups without overwriting later manual edits."""
    __tablename__ = 'practice_web_class_imports'
    teacher_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    school_key = Column(String(64), primary_key=True)
    level_key = Column(String(64), primary_key=True)
    class_id = Column(Integer, ForeignKey('practice_classes.id'), nullable=False)
