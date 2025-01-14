import time
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from packaging import version

from syftbox.lib.http import HEADER_GEO_COUNTRY, HEADER_OS_ARCH, HEADER_OS_NAME, HEADER_OS_VERSION, HEADER_SYFTBOX_PYTHON, HEADER_SYFTBOX_USER, HEADER_SYFTBOX_VERSION

MIN_SUPPORTED_VERSION = "0.3.0"

class LoguruMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.2f}s")

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_size_limit_in_mb = request.state.server_settings.request_size_limit_in_mb
        request_size_limit_in_bytes = request_size_limit_in_mb * 1024 * 1024

        content_length = request.headers.get("content-length")

        # If content-length header is present, check it first
        if content_length:
            if int(content_length) > request_size_limit_in_bytes:
                return Response(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content=f"Request Denied. Message size is greater than {request_size_limit_in_mb} MB",
                )

        # If content-length header is not present, read the request body and check its size.
        # TODO: This is susceptible to DoS attacks like Slowloris and body flooding. We should check
        # the request stream and terminate early as soon as the size exceeds the limit.
        request_body = await request.body()
        if len(request_body) > request_size_limit_in_bytes:
            return Response(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=f"Request Denied. Message size is greater than {request_size_limit_in_mb} MB",
            )

        response = await call_next(request)
        return response
    
class VersionCheckMIddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response: 
        logger.info(request.headers)
        client_version = request.headers.get(HEADER_SYFTBOX_VERSION.decode('utf-8'))
        if not client_version:
            return Response(
                status_code=status.HTTP_400_BAD_REQUEST,
                content="Client version not provided. Please include the 'Version' header."
            )
        
        if version.parse(client_version) < version.parse(MIN_SUPPORTED_VERSION):
            return Response(
                status_code=status.HTTP_426_UPGRADE_REQUIRED,
                content=f"Client version is too old. Minimum version required is {MIN_SUPPORTED_VERSION}",
            )
        
        response = await call_next(request)
        return response
