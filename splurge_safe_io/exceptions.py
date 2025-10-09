"""Custom exceptions used across the splurge-safe-io package.

This module defines a clear exception hierarchy so callers can catch
specific error categories (file, validation, parsing, streaming, etc.)
instead of dealing with generic builtins. Each exception stores a
human-readable ``message`` and optional ``details`` for diagnostic output.

Module contents are intentionally lightweight: exceptions are primarily
containers for structured error information.

Example:
    raise SplurgeSafeIoFileNotFoundError("File not found", details="/data/foo.csv")

License: MIT

Copyright (c) 2025 Jim Schilling
"""


class SplurgeSafeIoError(Exception):
    """Base exception carrying a message and optional details.

    Args:
        message (str): Primary error message to display to the user.
        details (str | None): Optional machine-readable details useful for debugging.
        original_exception (BaseException | None): Optional underlying builtin/exception that triggered this wrapper.

    Attributes:
        message: User-facing error message.
        details: Optional additional diagnostic information.
    """

    def __init__(
        self,
        message: str,
        *,
        details: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        self.message = message
        self.details = details
        # Preserve the underlying builtin exception for callers that
        # want programmatic access to the original error. Prefer passing
        # ``original_exception`` to the constructor when raising.
        self.original_exception: BaseException | None = original_exception
        super().__init__(self.message)


# New-style exception names. Use a SplurgeSafeIo* prefix to avoid colliding with
# Python builtins. We keep the Splurge* aliases for backward compatibility.


class SplurgeSafeIoFileOperationError(SplurgeSafeIoError):
    """Base exception for file operation errors.

    Used as a parent for file-related conditions such as not found,
    permission denied, or encoding issues.
    """


class SplurgeSafeIoFileNotFoundError(SplurgeSafeIoFileOperationError):
    """Raised when an expected file cannot be located.

    This typically maps to ``FileNotFoundError`` semantics but uses the
    package-specific exception hierarchy so callers can distinguish
    file errors from other error types.
    """


class SplurgeSafeIoFilePermissionError(SplurgeSafeIoFileOperationError):
    """Raised for permission or access-related file errors.

    For example, attempting to open a file without read permission will
    raise this exception.
    """


class SplurgeSafeIoFileDecodingError(SplurgeSafeIoFileOperationError):
    """Raised when decoding a text file fails.

    The exception typically wraps the underlying decoding error and
    provides a descriptive message and optional details for diagnostics.
    """


class SplurgeSafeIoFileEncodingError(SplurgeSafeIoFileOperationError):
    """Raised when decoding or encoding a text file fails.

    The exception typically wraps the underlying decoding error and
    provides a descriptive message and optional details for diagnostics.
    """


class SplurgeSafeIoStreamingError(SplurgeSafeIoFileOperationError):
    """Raised for errors during streaming (e.g., partial reads, IO interruptions)."""


class SplurgeSafeIoOsError(SplurgeSafeIoFileOperationError):
    """Raised for unexpected OS-level errors during file operations.

    This serves as a catch-all for unanticipated ``OSError`` conditions
    not covered by more specific exceptions.
    """


class SplurgeSafeIoFileAlreadyExistsError(SplurgeSafeIoFileOperationError):
    """Raised when a file that is being created already exists.

    This typically maps to ``FileExistsError`` semantics but uses the
    package-specific exception hierarchy so callers can distinguish
    file errors from other error types.
    """


class SplurgeSafeIoRuntimeError(SplurgeSafeIoError):
    """Raised for unexpected runtime errors within the package.

    This serves as a catch-all for unanticipated ``RuntimeError`` conditions
    not covered by more specific exceptions.
    """


class SplurgeSafeIoUnknownError(SplurgeSafeIoError):
    """Raised for completely unknown errors within the package.

    This serves as a catch-all for unanticipated conditions
    not covered by more specific exceptions.
    """


class SplurgeSafeIoConfigurationError(SplurgeSafeIoError):
    """Raised when an invalid configuration is provided to an API.

    Examples include invalid chunk sizes, missing delimiters, or mutually
    exclusive options supplied together.
    """


class SplurgeSafeIoValidationError(SplurgeSafeIoError):
    """Base exception for validation errors.

    Used as a parent for parameter, range, format, and other validation issues.
    """


class SplurgeSafeIoParameterError(SplurgeSafeIoValidationError):
    """Raised when a function or method receives invalid parameters.

    Use this for invalid types, missing required values, or arguments that
    violate expected constraints.
    """


class SplurgeSafeIoRangeError(SplurgeSafeIoValidationError):
    """Raised when a value falls outside an expected numeric or length range."""


class SplurgeSafeIoPathValidationError(SplurgeSafeIoValidationError):
    """Raised when a provided filesystem path fails validation checks.

    Use this exception for path traversal, dangerous characters, or other
    validation failures detected by the path validation utilities.
    """
