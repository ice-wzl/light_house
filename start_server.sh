#!/bin/bash

source venv/bin/activate
python3 -m uvicorn server.lighthouse:app --reload --host 0.0.0.0 --port 8000 --ssl-certfile certs/server.crt --ssl-keyfile certs/server.key > /dev/null 2>&1 &
