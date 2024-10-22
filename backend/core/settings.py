import typing as t
from decouple import config


###
# Cors & other security related stuff
###
CORS_ALLOWED_ORIGINS: list[str] = [
    "https://dialix.org",
    "https://dev.dialix.org",
    # local development
    "http://localhost:3000",
    "https://localhost:3000",
]

CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOWED_METHODS: list[str] = ["*"]
CORS_ALLOWED_HEADERS: list[str] = ["*"]

CORS_SETTINGS: dict[str, t.Any] = {
    "allow_credentials": CORS_ALLOW_CREDENTIALS,
    "allow_methods": CORS_ALLOWED_METHODS,
    "allow_headers": CORS_ALLOWED_HEADERS,
    "allow_origins": CORS_ALLOWED_ORIGINS,
}

###
# Database
###
DATABASE_URL: str = config("DATABASE_URL").replace("postgresql", "postgres")

TORTOISE_CONFIG: dict[str, t.Any] = {
    "connections": {
        "default": DATABASE_URL,
    },
    "apps": {
        "models": {
            "models": ["backend.database.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}

###
# Auth
###
ALGORITHM: str = config("AUTH_ALGORITHM")
SECRET_KEY: str = config("AUTH_SECRET_KEY")


###
# Other
##

PBX_API_URL = "https://api.onlinepbx.ru/{domain}"

# api.py is slowing down startup process.
# currently, I may not need this module
ENABLE_CORE_API_MODULE: bool = config("ENABLE_CORE_API_MODULE", cast=bool, default=True)
