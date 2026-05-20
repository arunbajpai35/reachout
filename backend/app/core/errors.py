class AppError(Exception):
    """Base error for the application. Carries an HTTP-friendly status."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class UpstreamError(AppError):
    """An external vendor (LLM, scraper, enrichment) failed in a non-retryable way."""

    status_code = 502
    code = "upstream_error"
