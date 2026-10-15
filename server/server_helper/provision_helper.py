#!/usr/bin/python3
import hashlib
import hmac
import re

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, String

from .db import Base, SessionLocal, get_db


AGENT_ID_PATTERN = r"^[0-9a-f]{32}$"
CREDENTIAL_HASH_PATTERN = r"^[0-9a-f]{64}$"
AGENT_SECRET_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class Provision(Base):
    __tablename__ = "provision"

    id = Column(String, primary_key=True, index=True)
    credential_hash = Column(String, nullable=False)
    status = Column(String, nullable=False, default="provisioned")
    created_at = Column(String, nullable=False)
    activated_at = Column(String, nullable=False, default="")


class ProvisionImplant(BaseModel):
    id: str = Field(pattern=AGENT_ID_PATTERN)
    credential_hash: str = Field(pattern=CREDENTIAL_HASH_PATTERN)


class ProvisionRead(BaseModel):
    id: str
    status: str
    created_at: str
    activated_at: str

    model_config = ConfigDict(from_attributes=True)


def _agent_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid agent credentials",
        headers={"WWW-Authenticate": "Agent"},
    )


def authenticate_agent(
    authorization: str = Header(default="", alias="Authorization"),
    db: SessionLocal = Depends(get_db),  # type: ignore
) -> Provision:
    try:
        scheme, credentials = authorization.split(" ", 1)
        agent_id, supplied_secret = credentials.split(":", 1)
    except ValueError:
        raise _agent_credentials_exception()

    if (
        scheme != "Agent"
        or re.fullmatch(AGENT_ID_PATTERN, agent_id) is None
        or AGENT_SECRET_PATTERN.fullmatch(supplied_secret) is None
    ):
        raise _agent_credentials_exception()

    provision = db.query(Provision).filter(Provision.id == agent_id).first()
    supplied_hash = hashlib.sha256(supplied_secret.encode("ascii")).hexdigest()

    if (
        provision is None
        or provision.status not in {"provisioned", "active"}
        or not hmac.compare_digest(provision.credential_hash, supplied_hash)
    ):
        raise _agent_credentials_exception()

    return provision


def authenticate_active_agent(
    provision: Provision = Depends(authenticate_agent),
) -> Provision:
    if provision.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent has not completed initial check-in",
        )
    return provision
