#!/usr/bin/python3
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# For OAuth2 Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str
