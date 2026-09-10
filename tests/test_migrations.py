from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from kivi.enums import EpistemicStatus, LifecycleStatus, MemoryType
from kivi.models import Memory, Project


def test_fresh_migration_creates_and_synchronizes_fts_index(tmp_path):
    database_path = tmp_path / "migrated.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with Session(engine) as session:
        session.add(Project(id="project-harbor", name="Project Harbor", aliases=[]))
        memory = Memory(
            id="mem_fts_test",
            project_id="project-harbor",
            memory_type=MemoryType.DECISION,
            subject="Project Harbor",
            predicate="release schedule",
            object_value="Thursday at 4 PM",
            epistemic_status=EpistemicStatus.APPROVED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            confidence=1.0,
            extraction_method="test",
            schema_version="1.0",
        )
        session.add(memory)
        session.commit()

        inserted = session.execute(
            text("SELECT object_value FROM memory_fts WHERE memory_fts MATCH 'Thursday'")
        ).scalar_one()
        assert inserted == "Thursday at 4 PM"

        memory.object_value = "Friday at 2 PM"
        session.commit()
        old_count = session.execute(
            text("SELECT count(*) FROM memory_fts WHERE memory_fts MATCH 'Thursday'")
        ).scalar_one()
        new_value = session.execute(
            text("SELECT object_value FROM memory_fts WHERE memory_fts MATCH 'Friday'")
        ).scalar_one()
        assert old_count == 0
        assert new_value == "Friday at 2 PM"

        session.delete(memory)
        session.commit()
        remaining = session.execute(text("SELECT count(*) FROM memory_fts")).scalar_one()
        assert remaining == 0
