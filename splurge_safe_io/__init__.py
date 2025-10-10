"""Public package surface for splurge_safe_io.

Keep imports light-weight to avoid heavy initialization at import time.
Expose commonly-used helpers and constants for convenience.
"""

from __future__ import annotations

__version__ = "2025.0.3"

# Public exports (import lazily to avoid side-effects)
from .constants import CANONICAL_NEWLINE, DEFAULT_ENCODING
from .exceptions import (
    SplurgeSafeIoConfigurationError,
    SplurgeSafeIoError,
    SplurgeSafeIoFileAlreadyExistsError,
    SplurgeSafeIoFileDecodingError,
    SplurgeSafeIoFileEncodingError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoFileOperationError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
    SplurgeSafeIoParameterError,
    SplurgeSafeIoPathValidationError,
    SplurgeSafeIoRangeError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoStreamingError,
    SplurgeSafeIoUnknownError,
    SplurgeSafeIoValidationError,
)

# Core helpers
from .path_validator import PathValidator
from .safe_text_file_reader import SafeTextFileReader, open_safe_text_reader
from .safe_text_file_writer import SafeTextFileWriter, TextFileWriteMode, open_safe_text_writer

__all__ = [
    "__version__",
    "CANONICAL_NEWLINE",
    "DEFAULT_ENCODING",
    "SplurgeSafeIoError",
    "SplurgeSafeIoFileOperationError",
    "SplurgeSafeIoFileNotFoundError",
    "SplurgeSafeIoFilePermissionError",
    "SplurgeSafeIoFileDecodingError",
    "SplurgeSafeIoFileEncodingError",
    "SplurgeSafeIoStreamingError",
    "SplurgeSafeIoOsError",
    "SplurgeSafeIoFileAlreadyExistsError",
    "SplurgeSafeIoRuntimeError",
    "SplurgeSafeIoUnknownError",
    "SplurgeSafeIoConfigurationError",
    "SplurgeSafeIoValidationError",
    "SplurgeSafeIoParameterError",
    "SplurgeSafeIoRangeError",
    "SplurgeSafeIoPathValidationError",
    "PathValidator",
    "SafeTextFileReader",
    "open_safe_text_reader",
    "SafeTextFileWriter",
    "open_safe_text_writer",
    "TextFileWriteMode",
]
