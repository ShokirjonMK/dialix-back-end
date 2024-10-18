from decouple import config
from redis_cache import RedisCache
from redis import StrictRedis, from_url


url = from_url(config("REDIS_URL", default="redis://localhost:6380/0"))
redis_client = StrictRedis(connection_pool=url.connection_pool)
cache = RedisCache(redis_client=redis_client)
