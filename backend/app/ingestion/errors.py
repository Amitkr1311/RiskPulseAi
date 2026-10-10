class ProviderError(Exception):
    """Sanitized provider failure that is safe to summarize in ingestion status."""

    category = "provider_error"
    retryable = False

    def __init__(self, message: str = "Provider request failed") -> None:
        super().__init__(message)


class ProviderNotConfiguredError(ProviderError):
    category = "not_configured"


class ProviderAuthenticationError(ProviderError):
    category = "authentication"


class ProviderRateLimitError(ProviderError):
    category = "rate_limit"
    retryable = True


class ProviderTimeoutError(ProviderError):
    category = "timeout"
    retryable = True


class ProviderTransientError(ProviderError):
    category = "transient"
    retryable = True


class ProviderResponseError(ProviderError):
    category = "malformed_response"


class ProviderValidationError(ProviderError):
    category = "validation"

