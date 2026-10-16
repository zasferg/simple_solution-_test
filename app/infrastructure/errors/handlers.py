from fastapi import Request
from fastapi.responses import JSONResponse

from app.infrastructure.errors.base import BaseError


async def base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """Registered for BaseError only; the signature matches Starlette's handler type."""
    if not isinstance(error, BaseError):
        raise error
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})
