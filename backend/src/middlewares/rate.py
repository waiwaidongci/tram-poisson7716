from fastapi.responses import JSONResponse
from redis import RedisError
from src.utils.wakeup import broker

limit = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""


def install(app):
    @app.middleware('http')
    async def burst_limit(request, call_next):
        if request.method == 'POST' and request.url.path == '/auth/login':
            # Nginx proxies all logins, so the limit is shared per stack.
            try:
                count = broker.eval(limit, 1, 'login-minute', 60)
                if count > 90:
                    return JSONResponse({'detail': '登录过于频繁，请稍后重试'}, 429)
            except RedisError:
                pass
        return await call_next(request)
