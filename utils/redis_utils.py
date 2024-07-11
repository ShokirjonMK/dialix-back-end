import os
from redis import StrictRedis, from_url
from redis_cache import RedisCache

url = from_url(os.getenv("REDIS_URL", "redis://localhost:6380/0"))
redis_client = StrictRedis(connection_pool=url.connection_pool)
cache = RedisCache(redis_client=redis_client)
