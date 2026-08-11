"""Application-level exceptions.

Services/repositories raise these instead of HTTPException directly, so
business logic stays decoupled from FastAPI/HTTP concerns. The handlers in
`app.middleware.error_handler` translate them into the documented
`{"error": {"code", "message", "request_id"}}` response shape.
"""


class AppException(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND", status_code=404)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message, code="CONFLICT", status_code=409)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="UNAUTHORIZED", status_code=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have access to this resource") -> None:
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ValidationAppError(AppException):
    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message, code="VALIDATION_ERROR", status_code=422)
