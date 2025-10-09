"""Deterministic text-only writer utilities.

This module implements :class:`SafeTextFileWriter` and a convenience
``open_text_writer`` context manager. Writes always use the configured
encoding and normalize newline characters to a canonical form (LF) to
ensure consistent files across platforms.

Example:
    with open_text_writer("out.txt") as buf:
        buf.write("line1\nline2\n")

Copyright (c) 2025 Jim Schilling
Please preserve this header and all related material when sharing!

License: MIT
"""

from __future__ import annotations

import io
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import cast

from splurge_safe_io.constants import CANONICAL_NEWLINE, DEFAULT_ENCODING
from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileAlreadyExistsError,
    SplurgeSafeIoFileEncodingError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
    SplurgeSafeIoParameterError,
    SplurgeSafeIoUnknownError,
)
from splurge_safe_io.path_validator import PathValidator


class TextFileWriteMode(Enum):
    """File write modes for SafeTextFileWriter."""

    CREATE_OR_TRUNCATE = "w"
    CREATE_OR_APPEND = "a"
    CREATE_NEW = "x"


class SafeTextFileWriter:
    """Helper for deterministic text writes with newline normalization.

    Use this class when you want predictable text file writes with
    canonical newline normalization. The class exposes a minimal
    file-like API (``write``, ``writelines``, ``flush``, ``close``) and
    performs deterministic error mapping to the package's exception
    hierarchy.

    Args:
        file_path (str | pathlib.Path): Destination file path.
        file_write_mode (TextFileWriteMode): How to open the file. Defaults
            to :data:`TextFileWriteMode.CREATE_OR_TRUNCATE`.
        encoding (str): Encoding used for writing. Defaults to
            :data:`splurge_safe_io.constants.DEFAULT_ENCODING`.
        canonical_newline (str): Newline sequence to use when normalizing
            incoming text. Defaults to :data:`splurge_safe_io.constants.CANONICAL_NEWLINE`.

    Raises:
        SplurgeSafeIoPathValidationError: If the provided path fails validation checks.
        SplurgeSafeIoFileAlreadyExistsError: If mode is CREATE_NEW and the file exists.
        SplurgeSafeIoFileEncodingError: If encoding fails.
        SplurgeSafeIoOsError: For unexpected OS-level errors.
        SplurgeSafeIoFilePermissionError: If the file cannot be opened due to permission issues.
        SplurgeSafeIoUnknownError: For other unexpected errors.
    """

    def __init__(
        self,
        file_path: Path | str,
        *,
        file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE,
        encoding: str = DEFAULT_ENCODING,
        canonical_newline: str = CANONICAL_NEWLINE,
    ) -> None:
        self._file_path = PathValidator.validate_path(
            file_path, must_exist=False, must_be_file=False, must_be_writable=False
        )
        self._encoding = encoding or DEFAULT_ENCODING
        self._file_write_mode = file_write_mode or TextFileWriteMode.CREATE_OR_TRUNCATE
        self._canonical_newline = canonical_newline or CANONICAL_NEWLINE
        # internal file object and thread-safe open flag
        self._file_obj: io.TextIOBase | None = None
        self._lock = threading.RLock()
        # open the file during initialization
        fp = self._open()
        with self._lock:
            self._file_obj = fp

    @property
    def file_path(self) -> Path:
        return Path(self._file_path)

    @property
    def file_write_mode(self) -> TextFileWriteMode:
        return TextFileWriteMode(self._file_write_mode)

    @property
    def encoding(self) -> str:
        return str(self._encoding)

    @property
    def canonical_newline(self) -> str:
        return str(self._canonical_newline)

    def _open(self) -> io.TextIOBase:
        """Open and return the underlying text file object.

        Returns:
            io.TextIOBase: Opened text file object ready for writes.

        Raises:
            SplurgeSafeIoFileAlreadyExistsError: If the file exists and mode is CREATE_NEW.
            SplurgeSafeIoFileEncodingError: If encoding fails when opening the file.
            SplurgeSafeIoFilePermissionError: If permission errors occur.
            SplurgeSafeIoOsError: For other OS-level errors.
            SplurgeSafeIoUnknownError: For unexpected errors.
        """
        try:
            # open with newline="" to allow us to manage newline normalization
            fp = open(self._file_path, mode=self._file_write_mode.value, encoding=self._encoding, newline="")
            # cast to TextIOBase for precise typing
            return cast(io.TextIOBase, fp)
        except FileExistsError as exc:
            raise SplurgeSafeIoFileAlreadyExistsError(
                f"File already exists: {self._file_path}", details=str(exc), original_exception=exc
            ) from exc  # pragma: no cover
        except UnicodeEncodeError as exc:
            raise SplurgeSafeIoFileEncodingError(str(exc), original_exception=exc) from exc  # pragma: no cover
        except PermissionError as exc:
            # Catch PermissionError explicitly before the more general OSError
            raise SplurgeSafeIoFilePermissionError(
                f"Permission error opening file: {self._file_path}", details=str(exc), original_exception=exc
            ) from exc  # pragma: no cover
        except OSError as exc:
            raise SplurgeSafeIoOsError(
                f"OS error opening file: {self._file_path}", details=str(exc), original_exception=exc
            ) from exc  # pragma: no cover
        except Exception as exc:
            raise SplurgeSafeIoUnknownError(
                f"Unexpected error opening file: {self._file_path}", details=str(exc), original_exception=exc
            ) from exc  # pragma: no cover

    def write(self, text: str) -> int:
        """Normalize newlines and write ``text`` to the opened file.

        Args:
            text (str): Text to write. Newline sequences will be normalized to
                ``self.canonical_newline`` before writing.

        Returns:
            int: Number of characters written to the underlying file object.

        Raises:
            SplurgeSafeIoFileEncodingError: If encoding fails.
            SplurgeSafeIoOsError: For OS-level write errors.
            SplurgeSafeIoUnknownError: For unexpected errors.
        """
        # Normalize outside the lock to minimize lock hold time
        normalized_text = text.replace("\r\n", self._canonical_newline).replace("\r", self._canonical_newline)

        # Hold the lock while checking and performing the write so that
        # close()/flush() cannot race with this write operation.
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoParameterError("File not opened")
            try:
                return self._file_obj.write(normalized_text)
            except UnicodeEncodeError as exc:
                raise SplurgeSafeIoFileEncodingError(str(exc), original_exception=exc) from exc  # pragma: no cover
            except OSError as exc:
                raise SplurgeSafeIoOsError(
                    "OS error writing to file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoUnknownError(
                    "Unexpected error writing to file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover

    def writelines(self, lines: Iterable[str]) -> None:
        """Write multiple lines to the opened file with newline normalization.

        Args:
            lines (Iterable[str]): Iterable of text lines to write. ``None``
                elements are ignored. If ``lines`` is None this method is a
                no-op.

        Returns:
            None

        Raises:
            SplurgeSafeIoFileEncodingError: If encoding fails.
            SplurgeSafeIoOsError: For OS-level write errors.
            SplurgeSafeIoUnknownError: For unexpected errors.
        """
        if lines is None:
            return

        normalized_parts = []
        # Normalize each line individually (do this outside the lock to
        # minimize contention) and collect them for a single write.
        for part in lines:
            if part is None:
                continue
            # Ensure the part is a str; let TypeErrors propagate if not.
            normalized = part.replace("\r\n", self._canonical_newline).replace("\r", self._canonical_newline)
            normalized_parts.append(normalized)

        # Join all normalized parts and write once atomically. We write
        # directly to the underlying file object under the lock to avoid
        # double-normalization (write() also normalizes) and to handle
        # exceptions in the same way as write().
        combined = "".join(normalized_parts)
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoParameterError("File not opened")
            try:
                # Write combined parts; do not return the underlying io write value
                self._file_obj.write(combined)
                return None
            except UnicodeEncodeError as exc:
                raise SplurgeSafeIoFileEncodingError(str(exc), original_exception=exc) from exc  # pragma: no cover
            except OSError as exc:
                raise SplurgeSafeIoOsError(
                    "OS error writing to file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoUnknownError(
                    "Unexpected error writing to file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover

    def flush(self) -> None:
        """Flush buffered writes to the underlying file.

        Raises:
            SplurgeSafeIoOsError: For OS-level errors during flush.
            SplurgeSafeIoUnknownError: For unexpected errors.
        """
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoParameterError("File not opened")
            try:
                self._file_obj.flush()
            except OSError as exc:
                raise SplurgeSafeIoOsError(
                    "OS error flushing file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoUnknownError(
                    "Unexpected error flushing file", details=str(exc), original_exception=exc
                ) from exc  # pragma: no cover

    def close(self) -> None:
        """Close the underlying file if opened.

        This method is idempotent; calling it multiple times has no effect.
        """
        # close file if open; set flag under lock to be thread-safe
        with self._lock:
            if self._file_obj is None:
                return
            try:
                self._file_obj.close()
            finally:
                self._file_obj = None


@contextmanager
def open_safe_text_writer(
    file_path: Path | str,
    *,
    encoding: str = DEFAULT_ENCODING,
    file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE,
    canonical_newline: str = CANONICAL_NEWLINE,
) -> Iterator[io.StringIO]:
    """Context manager yielding an in-memory StringIO to accumulate text.

    On successful exit, the buffered content is normalized and written to
    disk using :class:`SafeTextFileWriter`. If an exception occurs inside
    the context, nothing is written and the exception is propagated.

    Args:
        file_path: Destination path to write to on successful exit.
        encoding: Encoding to use when writing.
        file_write_mode: File open mode passed to writer (default: FileWriteMode.OVERWRITE_OR_CREATE).
        canonical_newline: Newline sequence to write (default: CANONICAL_NEWLINE).

    Raises:
        SplurgeSafeIoFileAlreadyExistsError: If the file exists and mode is CREATE_NEW.
        SplurgeSafeIoFileEncodingError: If the file cannot be opened with the requested encoding.
        SplurgeSafeIoOsError: If a general OS error occurs.
        SplurgeSafeIoFilePermissionError: If the file cannot be opened due to permission issues.
        SplurgeSafeIoFileOperationError: If an unexpected I/O error occurs.
        SplurgeSafeIoUnknownError: If an unexpected error occurs.

    Yields:
        io.StringIO: Buffer to write textual content into.

    Example:
        with open_safe_text_writer("out.txt") as buf:
            buf.write("line1\nline2\n")
    """
    buffer = io.StringIO()
    try:
        yield buffer
    except Exception:
        # Do not write on exceptions; re-raise
        raise
    else:
        content = buffer.getvalue()
        safe_writer = None
        try:
            safe_writer = SafeTextFileWriter(
                file_path=Path(file_path),
                encoding=encoding,
                file_write_mode=file_write_mode,
                canonical_newline=canonical_newline,
            )
            safe_writer.write(content)
            safe_writer.flush()
        finally:
            if safe_writer is not None:
                safe_writer.close()
