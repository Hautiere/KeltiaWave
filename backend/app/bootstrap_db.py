"""Create the shared Corpus/auth schema before Learning migrations.

Learning migrations reference the shared ``users`` table.  A new KeltiaWave
installation therefore needs the small shared schema before Alembic creates
the versioned Learning tables.
"""

from .db import Base, engine
from .models.audio import Audio, AudioValidation  # noqa: F401
from .models.phrase import Phrase  # noqa: F401
from .models.user import User  # noqa: F401


def create_shared_schema() -> None:
    shared_tables = [
        table
        for table in Base.metadata.sorted_tables
        if not table.name.startswith("learning_")
    ]
    Base.metadata.create_all(bind=engine, tables=shared_tables)


if __name__ == "__main__":
    create_shared_schema()
