"""Reuse the existing web teacher school/level profiles; never create accounts."""
import hashlib
import re
import secrets
import unicodedata
from .models.user import User
from .models.practice import PracticeClass, PracticeWebClassImport

SCHOOLS = {'ti-ar-vretonned': 'Ti ar vretonned', 'skol-an-emsav': 'Skol an emsav'}


def canonical(value):
    value = unicodedata.normalize('NFD', value.strip().lower())
    value = ''.join(char for char in value if unicodedata.category(char) != 'Mn')
    return re.sub(r'\s+', '-', value.replace('_', '-'))


def sync_web_formations(db):
    # Lock the existing teachers to serialize concurrent application startups.
    teachers = (db.query(User).filter(User.role == 'teacher', User.active == True)
                .order_by(User.id).with_for_update().all())
    for teacher in teachers:
        schools = {}
        for value in [teacher.school, teacher.organization]:
            for item in re.split(r'[;,]', value or ''):
                if item.strip():
                    key = canonical(item)
                    schools.setdefault(key, SCHOOLS.get(key, item.strip()))
        level = (teacher.school_level or '').strip()
        match = re.fullmatch(r'niveau[- _]*(\d+)', level, re.IGNORECASE)
        name = f'Niveau {match[1]}' if match else level or f'Classe de {teacher.display_name}'
        for school_key, school_name in schools.items():
            identity = (teacher.id, hashlib.sha256(school_key.encode()).hexdigest(),
                        hashlib.sha256(canonical(level).encode()).hexdigest())
            if db.get(PracticeWebClassImport, identity):
                continue
            existing = db.query(PracticeClass).filter(PracticeClass.teacher_id == teacher.id).all()
            cls = next((row for row in existing if canonical(row.school) == school_key and canonical(row.name) == canonical(name)), None)
            if not cls:
                cls = PracticeClass(name=name[:120], school=school_name[:160], teacher_id=teacher.id, code=secrets.token_hex(6).upper())
                db.add(cls); db.flush()
            db.add(PracticeWebClassImport(teacher_id=identity[0], school_key=identity[1], level_key=identity[2], class_id=cls.id))
    db.commit()
