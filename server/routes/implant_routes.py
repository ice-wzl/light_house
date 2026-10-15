from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Security
from sqlalchemy.exc import SQLAlchemyError

from server.server_helper.auth_helper import oauth2_scheme, verify_token
from server.server_helper.db import get_db, SessionLocal
from server.server_helper.implant_helper import Implant, ImplantCreate, ImplantRead
from server.server_helper.provision_helper import Provision, authenticate_agent

router = APIRouter(prefix="/implants", tags=["implants"])

# endpoint for agent initial checkin, register with server for future tasking/results/tracking
@router.post("/", response_model=ImplantRead)
def create_implant(
    implant: ImplantCreate,
    db: SessionLocal = Depends(get_db),  # type: ignore
    provision: Provision = Depends(authenticate_agent),
):
    current_time = datetime.now(timezone.utc).isoformat()

    if implant.session != provision.id:
        raise HTTPException(status_code=403, detail="Agent cannot use this session")

    existing_implant = (
        db.query(Implant).filter(Implant.session == provision.id).first()
    )
    if existing_implant is not None:
        if provision.status == "active":
            return existing_implant
        raise HTTPException(status_code=409, detail="Session is already registered")

    if provision.status != "provisioned":
        raise HTTPException(status_code=409, detail="Agent cannot be activated")

    implant_data = implant.model_dump(
        exclude={"alive", "first_checkin", "last_checkin"}
    )

    db_implant = Implant(
        **implant_data,
        alive=True,
        first_checkin=current_time,
        last_checkin=current_time,
    )

    provision.status = "active"
    provision.activated_at = current_time

    try:
        db.add(db_implant)
        db.commit()
        db.refresh(db_implant)
    except SQLAlchemyError:
        db.rollback()
        raise

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
