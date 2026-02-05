#!/usr/bin/python3
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

# local imports
from .db import Base


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(String, default=datetime.now(timezone.utc).isoformat())


class UserCreate(BaseModel):
    username: str
    password: str
    created_at: str = datetime.now(timezone.utc).isoformat()


class UserRead(UserCreate):
    id: int

    class Config:
        form_attributes = True


class UserDelete(BaseModel):
    id: int

class UsersDeleteUsername(BaseModel):
    username: str
