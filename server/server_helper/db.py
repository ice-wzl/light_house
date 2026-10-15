#!/usr/bin/python3
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "db" / "database.db"
)
DATABASE_URL = os.environ.get(
    "LIGHTHOUSE_DATABASE_URL",
    f"sqlite:///{DEFAULT_DATABASE_PATH}",
)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
