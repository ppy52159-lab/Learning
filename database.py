from sqlmodel import SQLModel, create_engine, Session
from config import settings  # <-- IMPORT SETTINGS!
from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
# Read DATABASE_URL dynamically!
'''connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
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
		'''
        
        
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
    
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
                