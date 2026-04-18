class AutoFillError(Exception):
    """Base exception for AutoFill application."""


class InvalidFileTypeError(AutoFillError):
    """Raised when file type is not supported."""


class SourceReadError(AutoFillError):
    """Raised when source document cannot be read."""


class LlmRequestError(AutoFillError):
    """Raised when LLM request fails (network/timeout/rate-limit)."""


class NonJsonResponseError(AutoFillError):
    """Raised when LLM output is not valid JSON."""


class SchemaValidationError(AutoFillError):
    """Raised when parsed JSON does not meet expected structure constraints."""


class TemplateVariableMissingError(AutoFillError):
    """Raised when required template variables are missing from context."""


class RenderError(AutoFillError):
    """Raised when docx rendering fails."""

