import time
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_SIZE_LIMIT_IN_MB = 10

class LoguruMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.2f}s")

        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_body = await request.body()
        if len(request_body) > REQUEST_SIZE_LIMIT_IN_MB * 1024 * 1024:
            return Response(status_code=413, content=f"Request Denied. Message size is greater than {REQUEST_SIZE_LIMIT_IN_MB} MB")

        response = await call_next(request)
        return response
    
    