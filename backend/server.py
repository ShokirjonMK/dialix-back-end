import os
import sys
import logging
import datetime
from platform import node as get_hostname

from tortoise import connections

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.sockets import sio_app
from backend.core.lifespan import lifespan_handler
from backend.core.logging import configure_logging
from backend.core.exceptions import register_exception_handlers

from backend.routers.user import user_router
from backend.routers.checklist import checklist_router

from backend.core import settings

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

application = FastAPI(lifespan=lifespan_handler)

configure_logging()
register_exception_handlers(application)

application.mount("/ws/", app=sio_app)


###
# Setup Routers
###
ROUTERS = [user_router, checklist_router]

if settings.ENABLE_CORE_API_MODULE:
    from backend.api import api_router

    ROUTERS.append(api_router)
else:
    logging.warning(
        "CORE API module (api.py) is currently disabled for development purposes. "
        "Refer to 'settings.py' to enable it"
    )
for router in ROUTERS:
    application.include_router(router)

###
# Tensorflow & NVIDIA Cuda
###
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

###
# Middleware setup
###
application.add_middleware(CORSMiddleware, **settings.CORS_SETTINGS)


@application.get("/health")
async def healthcheck():
    connection = connections.get("default")
    db_version_record: None = None

    try:
        db_version_record = await connection.execute_query("select version();")
        db_version = db_version_record[1][0]["version"]
    except Exception as exc:
        logging.error(f"Can't connect to database: {exc=} {db_version_record=}")
        db_version = None

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "database": db_version,
            "hostname": get_hostname(),
            "time": datetime.datetime.now().isoformat(),
            "status": "!ok" if db_version is None else "ok",
        },
    )
