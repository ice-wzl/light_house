import base64
import binascii
from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI, HTTPException, status, Depends, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional, List
from fastapi.security import OAuth2PasswordRequestForm

# CORRECT imports when you're inside the 'server' package
from server_helper.user_helper import Users, UserRead, UserCreate, UserDelete
from server_helper.auth_helper import oauth2_scheme, verify_token
from server_helper.db import get_db, SessionLocal
from server_helper.auth_helper import Token, oauth2_scheme

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

router = APIRouter(prefix="/token", tags=["token"])

# for client only to be able to access protected endpoints, authentication via OAuth2
@router.post("/", response_model=Token)
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
