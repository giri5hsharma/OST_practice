# to be imported by main and schemas files
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db" # tells sqlalchemy where to connect

engine = create_async_engine( #connection to the db
    SQLALCHEMY_DATABASE_URL,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
#creates database session. a session is a transaction with the db.
#autocommit and autoflush are set to false because we want to control when we commit and flush the session.

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as db: #makes session work as a context manager.
        #it calls a dependency injection; this route needs a db session, give it one
        yield db

#DATABASE MODELS --> TABLES
