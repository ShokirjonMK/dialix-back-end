import typing as t
from decouple import config


###
# Cors & other security related stuff
###
CORS_ALLOWED_ORIGINS: list[str] = [
    "https://dialix.org",
    "https://new.dialix.org",
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
# Third Party
###
MOHIRAI_API_KEY: str = config("MOHIRAI_API_KEY")
PBX_API_URL = "https://api.onlinepbx.ru/{domain}"
MOHIRAI_API_URL: str = "https://uzbekvoice.ai/api/v1/stt"


###
# Database
###
DATABASE_URL: str = config("DATABASE_URL")
ECHO_SQL: bool = config("ECHO_SQL", cast=bool, default=False)

###
# Auth
###
ALGORITHM: str = config("AUTH_ALGORITHM")
SECRET_KEY: str = config("AUTH_SECRET_KEY")

###
# Pricing
###
MOHIRAI_PRICE_PER_MS: float = 630 / 60 / 1000 * 100
GENERAL_PROMPT_PRICE_PER_MS: float = 210 / 60 / 1000 * 100
CHECKLIST_PROMPT_PRICE_PER_MS: float = 360 / 60 / 1000 * 100

# slowing down startup process.
# currently, I may not need this module
ANTI_SLOW_DOWN: bool = config("ANTI_SLOW_DOWN", cast=bool, default=False)

###
# Redis Configuration
###
REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")
REDIS_CACHE_TTL: int = config("REDIS_CACHE_TTL", cast=int, default=300)  # 5 minutes

###
# Monitoring & Observability
###
ENABLE_APM: bool = config("ENABLE_APM", cast=bool, default=False)
SENTRY_DSN: str = config("SENTRY_DSN", default="")
