from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

__all__ = [
    "AsyncRetrying",
    "RetryError",
    "retry_if_exception_type",
    "stop_after_attempt",
    "wait_exponential_jitter",
    "default_retry",
]


def default_retry(
    *, attempts: int = 3, max_wait: float = 10.0, retry_on: type[BaseException] = Exception
) -> AsyncRetrying:
    """Standard retry policy for upstream calls: 3 attempts, exp backoff with jitter."""
    return AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=0.5, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    )
