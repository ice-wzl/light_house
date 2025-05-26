#!/usr/bin/python3
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

# local imports
from server_helper.db import Base

class Results(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    tasking_id = Column(Integer, ForeignKey('tasking.id', ondelete="CASCADE"), nullable=False)
    session = Column(String, ForeignKey('implants.session', ondelete="CASCADE"), nullable=False)
    date = Column(String)
    task = Column(String)
    args = Column(String)
    results = Column(String)
    implant = relationship("Implant", backref="results")

class ResultsCreate(BaseModel):
    tasking_id: int
    session: Optional[str] = None  #implant handles
    date: Optional[str] = None     #server handles
    task: Optional[str] = None     #implant handles
    args: Optional[str] = None     #implant handles
    results: Optional[str] = None  #implant handles

# only client ensure auth 
class ResultsRead(ResultsCreate):
    id: int

    class Config:
        form_attributes = True 

# only client ensure auth
class ResultsDelete(BaseModel):
    id: int
    session: str