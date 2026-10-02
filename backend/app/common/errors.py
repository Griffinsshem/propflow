"""Structured error responses. Internals never reach the client; details go to logs."""

from __future__ import annotations

from typing import Any

import structlog
from flask import Flask, Response, g, jsonify
from werkzeug.exceptions import HTTPException

logger = structlog.get_logger("propflow.errors")


class AppError(Exception):
    """Base class for expected, client-safe application errors."""

    status_code = 400
    code = "BAD_REQUEST"
    message = "The request could not be processed."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class RequestValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "The request contains invalid data."


class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    message = "Authentication is required."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    """Also used for other organizations' resources, so their existence is never confirmed."""

    status_code = 404
    code = "RESOURCE_NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "The request could not be processed."),
    401: ("UNAUTHENTICATED", "Authentication is required."),
    403: ("FORBIDDEN", "You do not have permission to perform this action."),
    404: ("RESOURCE_NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "This method is not allowed for this resource."),
    409: ("CONFLICT", "The request conflicts with the current state of the resource."),
    413: ("PAYLOAD_TOO_LARGE", "The request body is too large."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "The request content type is not supported."),
    422: ("VALIDATION_ERROR", "The request contains invalid data."),
    429: ("RATE_LIMITED", "Too many requests. Please try again later."),
}
_INTERNAL_ERROR = ("INTERNAL_ERROR", "An unexpected error occurred.")


def error_response(
    status: int, code: str, message: str, details: Any = None
) -> tuple[Response, int]:
    payload: dict[str, Any] = {"code": code, "message": message, "request_id": g.get("request_id")}
    if details is not None:
        payload["details"] = details
    return jsonify({"error": payload}), status


def register_error_handlers(app: Flask) -> None:
    """Call AFTER flask-smorest's Api(app) so these handlers replace its defaults."""

    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError) -> tuple[Response, int]:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException) -> tuple[Response, int]:
        status = exc.code or 500
        if status >= 500:
            code, message = _INTERNAL_ERROR
        else:
            code, message = _HTTP_ERRORS.get(status, ("BAD_REQUEST", "The request failed."))
        details = None
        if status == 422:
            # webargs/flask-smorest put field-level messages here (field names, never values).
            details = (getattr(exc, "data", None) or {}).get("messages")
        return error_response(status, code, message, details)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception) -> tuple[Response, int]:
        logger.error("unhandled_exception", error_type=type(exc).__name__, exc_info=exc)
        return error_response(500, *_INTERNAL_ERROR)


class OrganizationContextError(AppError):
    """No valid organization context: none selected, membership removed, or org suspended."""

    status_code = 403
    code = "ORGANIZATION_CONTEXT_REQUIRED"
    message = "Select an organization you belong to before continuing."
