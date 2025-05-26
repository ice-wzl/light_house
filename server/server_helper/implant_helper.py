#!/usr/bin/python3
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, Text

# local imports
from server_helper.db import Base

class Implant(Base):
    __tablename__ = "implants"
    id =            Column(Integer, primary_key=True, index=True)
    session =       Column(String, unique=True, nullable=False)
    first_checkin = Column(String)
    last_checkin =  Column(String)
    alive =         Column(Boolean)
    callback_freq = Column(Integer)
    jitter =        Column(Integer)
    username =      Column(Text)
    hostname =      Column(Text)


class ImplantCreate(BaseModel):
    session:        Optional[str] = None
    first_checkin:  Optional[str] = None
    last_checkin:   Optional[str] = None
    alive:          Optional[bool] = False
    callback_freq:  Optional[int] = 0
    jitter:         Optional[int] = 0
    username:       Optional[str] = None
    hostname:       Optional[str] = None

class ImplantRead(ImplantCreate):
    id: int

    class Config:
        form_attributes = True