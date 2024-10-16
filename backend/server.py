import os
import sys
import datetime
from platform import node as get_hostname

from fastapi import FastAPI, status

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.api import api_router
from backend.sockets import sio_app
from backend.core.lifespan import lifespan_handler
from backend.core.logging import configure_logging
from backend.core.exceptions import register_exception_handlers  # noqa: F401

from backend.routers.user import user_router

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

application = FastAPI(lifespan=lifespan_handler)

configure_logging()
register_exception_handlers(application)

application.mount("/ws/", app=sio_app)
application.include_router(user_router)
application.include_router(api_router)

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

origins: list[str] = [
    "https://dialix.org",
    "https://dev.dialix.org",
    # local development
    "http://localhost:3000",
    "https://localhost:3000",
]

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.get("/health")
def health():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "hostname": get_hostname(),
            "time": datetime.datetime.now().isoformat(),
        },
    )
