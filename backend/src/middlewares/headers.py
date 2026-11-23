from uuid import uuid4
from fastapi.responses import JSONResponse


def install(app):
    @app.middleware('http')
    async def request_headers(request, call_next):
        length = request.headers.get('content-length', '0')
        if not length.isdecimal() or int(length) > 4_194_304:
            return JSONResponse({'detail': '请求体不能超过 4 MB'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Request-ID'] = uuid4().hex
        response.headers['Cache-Control'] = 'no-store'
        return response
