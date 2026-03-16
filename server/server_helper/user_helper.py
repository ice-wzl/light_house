#!/usr/bin/python3
import hashlib 
import string
import random
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

# local imports
from .db import Base


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    salt = Column(String, unique=False, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(String, default=datetime.now(timezone.utc).isoformat())


class UserCreate(BaseModel):
    username: str
    password: str
    created_at: str = datetime.now(timezone.utc).isoformat()


class UserRead(BaseModel):
    id: int
    username: str
    created_at: str

    class Config:
        form_attributes = True


class UserDelete(BaseModel):
    id: int

class UsersDeleteUsername(BaseModel):
    username: str

def get_salt():
    return ''.join(random.choices(string.ascii_letters, k=8))

def hash_password(salt: str, password_cleartext: str):
    password_combined = salt.encode("utf-8") + password_cleartext.encode("utf-8")
    hashed = hashlib.sha512(password_combined)
    return hashed.hexdigest()