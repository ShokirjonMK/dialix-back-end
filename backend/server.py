import os
import sys
import datetime
from platform import node as get_hostname

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.sockets import sio_app
from backend.core.lifespan import lifespan_handler
from backend.core.logging import configure_logging

from backend.core.exceptions import register_exception_handlers
from backend.core.dependencies import DatabaseSessionDependency

from backend.api import api_router
from backend.routers.pbx import pbx_router
from backend.routers.user import user_router
from backend.routers.operator import operator_router
from backend.routers.checklist import checklist_router

from backend.core import settings
from backend.utils.healthcheck import is_db_working

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

application = FastAPI(lifespan=lifespan_handler)

configure_logging()
register_exception_handlers(application)

application.mount("/ws/", app=sio_app)


###
# Setup Routers
###
ROUTERS = [user_router, checklist_router, pbx_router, api_router, operator_router]

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
async def healthcheck(db_session: DatabaseSessionDependency):
    db_status = is_db_working()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "is_db_working": db_status,
            "hostname": get_hostname(),
            "time": datetime.datetime.now().isoformat(),
            "status": "!ok" if not db_status else "ok",
        },
    )
