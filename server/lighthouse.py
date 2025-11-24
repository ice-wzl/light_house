#!/usr/bin/python3
import argparse
import base64
import binascii
import uvicorn
import re
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import FastAPI, HTTPException, status, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse

# local imports
from server_helper.auth_helper import Token, oauth2_scheme
from server_helper.auth_helper import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from server_helper.user_helper import Users, UserCreate, UserRead, UserDelete
from server_helper.db import Base, SessionLocal

from server_helper.db import get_db
from server_helper.auth_helper import verify_token
from server_helper.auth_helper import create_access_token

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

from server_helper.lighthouse_config import *

app = FastAPI()
from routes.user_routes import router as user_router
from routes.health_routes import router as health_router
from routes.results_routes import router as results_router
from routes.implant_routes import router as implant_router
from routes.task_routes import router as task_router
from routes.tasking_routes import router as tasking_router
from routes.token_routes import router as token_router

app.include_router(user_router)
app.include_router(health_router)
app.include_router(results_router)
app.include_router(implant_router)
app.include_router(task_router)
app.include_router(tasking_router)
app.include_router(token_router)

if __name__ == '__main__':
    opts = argparse.ArgumentParser(description="light_house server application")
    opts.add_argument("-c", "--config", help="the light_house config file containing runtime variables", required=True, type=str, default="lighthouse.conf", dest="config")
    args = opts.parse_args()
    
    conf = parse_config(args.config)
    web_server = parse_config_vals(conf)
    uvicorn.run(app, host=web_server.listen_host, port=web_server.listen_port, ssl_certfile=web_server.server_crt, ssl_keyfile=web_server.server_key)

