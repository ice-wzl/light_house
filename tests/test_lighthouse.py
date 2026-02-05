import pytest
import os

from httpx import codes
from fastapi.testclient import TestClient
from server.lighthouse import app

# local imports
from server.server_helper.auth_helper import Token, oauth2_scheme
from server.server_helper.auth_helper import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from server.server_helper.user_helper import Users, UserCreate, UserRead, UserDelete
from server.server_helper.db import Base, SessionLocal

from server.server_helper.db import get_db

from server.server_helper.implant_helper import Implant, ImplantCreate, ImplantRead
from server.server_helper.tasking_helper import (
    Tasking,
    TaskingCreate,
    TaskingRead,
    TaskingDelete,
)
'''
endpoints:

POST /implants
GET /implants
GET /implants/{session}

GET /results/{session}/{id}
POST /results/{session}

GET /tasks/{session}

GET /tasking/{session}
POST /tasking/{session}

POST /token

GET /users
GET /users/{id}
DELETE /users/delete/{user_id}
POST /users/{create}

'''

from server.server_helper.results_helper import (
    Results,
    ResultsCreate,
    ResultsRead,
    ResultsDelete,
)

client = TestClient(app)

os.system("cd db/ && ./reset_db.sh")






    