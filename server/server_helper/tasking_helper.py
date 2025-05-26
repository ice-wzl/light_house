#!/usr/bin/python3
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

# local imports
from server_helper.db import Base


class Tasking(Base):
    __tablename__ = "tasking"
    id = Column(Integer, primary_key=True, index=True)
    session = Column(String, ForeignKey('implants.session', ondelete="CASCADE"), nullable=False)
    date = Column(String)
    task = Column(String)
    args = Column(String)
    complete = Column(String, default="False")
    implant = relationship("Implant", backref="taskings")

class TaskingCreate(BaseModel):
    session: Optional[str] = None
    date: Optional[str] = None
    task: Optional[str] = None
    args: Optional[str] = None
    complete: Optional[str] = "False"

class TaskingRead(TaskingCreate):
    id: int

    class Config:
        form_attributes = True

class TaskingDelete(BaseModel):
    id: int
    session: str