from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from server.server_helper.user_helper import Users
from server.server_helper.auth_helper import Token, create_access_token, check_password_hash
from server.server_helper.db import get_db, SessionLocal

router = APIRouter(prefix="/token", tags=["token"])

# for client only to be able to access protected endpoints, authentication via OAuth2
@router.post("/", response_model=Token)
def login(
    db: SessionLocal = Depends(get_db),  # type: ignore
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user_entry = (db.query(Users).filter(Users.username == form_data.username).first())
    if not user_entry:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    valid_password = check_password_hash(user_entry.salt, form_data.password, user_entry.password)
    if valid_password:
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid username or password")
