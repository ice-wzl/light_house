#!/usr/bin/python3
import argparse
import sys
from pathlib import Path

# Add project root to path for running from project root: python server/lighthouse.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI

from server.server_helper.lighthouse_config import parse_config, parse_config_vals

from server.routes.user_routes import router as user_router
from server.routes.health_routes import router as health_router
from server.routes.results_routes import router as results_router
from server.routes.implant_routes import router as implant_router
from server.routes.task_routes import router as task_router
from server.routes.tasking_routes import router as tasking_router
from server.routes.token_routes import router as token_router

app = FastAPI()

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

