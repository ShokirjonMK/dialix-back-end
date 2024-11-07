import os
import logging
import socketio
from decouple import config
from fastapi import HTTPException
from backend.core import auth
from http.cookies import SimpleCookie

from backend.database.session_manager import get_db_session

REDIS_URL: str = config("REDIS_URL")

redis_manager = socketio.AsyncRedisManager(REDIS_URL)

sio_server = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=redis_manager,
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)

sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path="/ws/socket.io",
)


@sio_server.event
async def connect(sid, environ):
    logging.warning("In the connect event")
    try:
        logging.warning(f"Connected sid={sid}")

        cookie_header = environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_header)

        access_token = (
            cookie.get("access_token").value if "access_token" in cookie else None
        )
        if access_token:
            user = dict(
                await auth.get_current_user_websocket(
                    access_token, next(get_db_session())
                )
            )
            await sio_server.save_session(sid, {"user": user})
            await sio_server.enter_room(sid, f"user/{user['id']}")
        else:
            logging.warning(f"No access token provided for sid={sid}")
            await sio_server.disconnect(sid)
    except HTTPException as e:
        logging.warning(f"Failed to connect sid={sid} error={e}")
        raise


@sio_server.event
async def disconnect(sid):
    logging.warning("In the disconnect event")
    session = await sio_server.get_session(sid)
    await sio_server.leave_room(sid, f"user/{session['user']['id']}")
    logging.warning(f"Disconnected sid={sid}")
