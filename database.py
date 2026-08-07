from sqlmodel import SQLModel, create_engine, Session
from config import settings  # <-- IMPORT SETTINGS!

# Read DATABASE_URL dynamically!
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
# SQLite Database setup
sqlite_file_name = "task_master.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# connect_args={"check_same_thread": False} is required for SQLite in FastAPI
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
		