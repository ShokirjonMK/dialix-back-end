import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import backend.db
import backend.api
import backend.sockets
from backend.app import app


if __name__ == "__main__":
    import uvicorn

    print("Starting app...")
    uvicorn.run(app, host="0.0.0.0", port=8081)
