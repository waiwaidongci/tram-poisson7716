import logging
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

log = logging.getLogger(__name__)


def install(app):
    @app.exception_handler(ValueError)
    async def bad_input(request, error):
        return JSONResponse({'detail': str(error)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def bad_request(request, error):
        fields = '、'.join('.'.join(str(part) for part in issue['loc'][1:]) for issue in error.errors())
        return JSONResponse({'detail': f'请求字段有误，请检查 {fields}'}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        log.error('Unhandled %s %s', request.method, request.url.path, exc_info=error)
        return JSONResponse({'detail': '服务操作失败，请重试'}, status_code=500)
