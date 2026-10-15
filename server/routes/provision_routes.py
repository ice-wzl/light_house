from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.exc import IntegrityError

from server.server_helper.auth_helper import oauth2_scheme, verify_token
from server.server_helper.db import SessionLocal, get_db
from server.server_helper.provision_helper import (
    Provision,
    ProvisionImplant,
    ProvisionRead,
)


router = APIRouter(prefix="/provision", tags=["provision"])


@router.post("/", response_model=ProvisionRead, status_code=status.HTTP_201_CREATED)
def provision_implant(
    provision_implant: ProvisionImplant,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    verify_token(token)

    if db.query(Provision).filter(Provision.id == provision_implant.id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent is already provisioned",
        )

    db_provision = Provision(
        id=provision_implant.id,
        credential_hash=provision_implant.credential_hash,
        status="provisioned",
        created_at=datetime.now(timezone.utc).isoformat(),
        # The existing schema requires a value before activation.
        activated_at="",
    )

    try:
        db.add(db_provision)
        db.commit()
        db.refresh(db_provision)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent is already provisioned",
        )

    return db_provision


@router.delete("/{agent_id}", response_model=ProvisionRead)
def revoke_implant(
    agent_id: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    token: str = Security(oauth2_scheme),
):
    verify_token(token)

    db_provision = db.query(Provision).filter(Provision.id == agent_id).first()
    if db_provision is None:
        raise HTTPException(status_code=404, detail="Provisioned agent not found")

    db_provision.status = "revoked"
    db.commit()
    db.refresh(db_provision)
    return db_provision
