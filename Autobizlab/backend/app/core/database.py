"""
Драйвер доступа к PostgreSQL через SQLAlchemy 2.0 (драйвер psycopg v3).

Строка подключения задаётся в `Settings.database_url`, в compose —
`postgresql+psycopg://USER:PASSWORD@postgres:5432/DB`.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        future=True,
    )


engine = _engine()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
