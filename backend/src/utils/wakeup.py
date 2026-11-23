from redis import Redis, RedisError
from src.config.settings import QUEUE, REDIS_URL

broker = Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=4)


def wake():
    try:
        with broker.pipeline() as pipe:
            pipe.lpush(QUEUE, 'work').ltrim(QUEUE, 0, 99).execute()
    except RedisError:
        # SQL remains authoritative. The worker also polls for jobs.
        pass


def wait():
    broker.brpop(QUEUE, timeout=2)
