import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"


class MissingIdentityError(AuthenticationError):
    code = "MISSING_IDENTITY"


class UnknownIdentityError(AuthenticationError):
    code = "UNKNOWN_IDENTITY"


class AuthorizationError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ApprovalLimitExceededError(AuthorizationError):
    code = "APPROVAL_LIMIT_EXCEEDED"


class ActionNotPermittedForRoleError(AuthorizationError):
    code = "ACTION_NOT_PERMITTED_FOR_ROLE"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class InvalidStateTransitionError(AppError):
    status_code = 409
    code = "INVALID_STATE_TRANSITION"


class UnsupportedCurrencyError(ValidationError):
    code = "UNSUPPORTED_CURRENCY"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        error = ValidationError(
            "Request validation failed.",
            details={"errors": [_serialize_pydantic_error(e) for e in exc.errors()]},
        )
        return JSONResponse(status_code=error.status_code, content=error.to_payload())

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled %s while handling %s %s",
            type(exc).__name__,
            request.method,
            request.url.path,
            exc_info=exc,
        )
        error = AppError("An unexpected error occurred.")
        return JSONResponse(status_code=error.status_code, content=error.to_payload())


def _serialize_pydantic_error(err: dict[str, Any]) -> dict[str, Any]:
    return {
        "loc": [str(part) for part in err.get("loc", [])],
        "msg": err.get("msg", ""),
        "type": err.get("type", ""),
    }
