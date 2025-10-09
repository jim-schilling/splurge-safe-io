"""Comprehensive usage examples for splurge-safe-io.

This script demonstrates common workflows and error handling patterns:

- Validating paths with PathValidator
- Writing text deterministically with SafeTextFileWriter and open_safe_text_writer
- Reading with SafeTextFileReader and open_safe_text_reader
- Streaming reads with read_as_stream()
- Inspecting mapped exceptions and the `original_exception` attribute

Run this script as a developer reference. It is intended for interactive
exploration and documentation; it does not require installation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from splurge_safe_io.exceptions import (
    SplurgeSafeIoError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
)
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter, open_safe_text_writer


def demo_path_validation(tmp_dir: Path) -> None:
    print("\n== Path validation demo ==")
    p = tmp_dir / "example.txt"

    # Validate a path before using it. This will resolve and normalize.
    try:
        resolved = PathValidator.validate_path(p, must_exist=False)
        print("Resolved:", resolved)
    except SplurgeSafeIoError as exc:
        print("Path validation failed:", exc)


def demo_write_and_read(tmp_dir: Path) -> None:
    print("\n== Write + Read demo ==")
    dest = tmp_dir / "sample.txt"

    # Use the context-manager helper to build content in-memory and write
    with open_safe_text_writer(dest, encoding="utf-8") as buf:
        buf.write("First line\r\nSecond line\nThird line")

    # Read back with SafeTextFileReader (normalizes newlines, strips by default)
    reader = SafeTextFileReader(dest, encoding="utf-8", strip=True)
    lines = reader.read()
    print("Read lines:")
    for ln in lines:
        print(repr(ln))


def demo_streaming(tmp_dir: Path) -> None:
    print("\n== Streaming demo ==")
    dest = tmp_dir / "big.txt"

    # Create a file with many lines
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        for i in range(1, 501):
            fh.write(f"line {i}\n")

    reader = SafeTextFileReader(dest, chunk_size=100, strip=False)
    chunk_count = 0
    for _ in reader.read_as_stream():
        chunk_count += 1
    print(f"Streamed in {chunk_count} chunks (chunk_size={reader.chunk_size})")


def demo_error_inspection(tmp_dir: Path) -> None:
    print("\n== Error inspection demo ==")
    missing = tmp_dir / "does-not-exist.txt"

    try:
        SafeTextFileReader(missing).read()
    except SplurgeSafeIoFileNotFoundError as err:
        print("Caught mapped FileNotFoundError -> SplurgeSafeIoFileNotFoundError")
        print("message:", err.message)
        print("details:", err.details)
        print("__cause__:", repr(err.__cause__))
        print("original_exception:", repr(getattr(err, "original_exception", None)))
    except SplurgeSafeIoError as err:
        print("Other splurge-safe-io error:", err)

    # Demonstrate catching the generic mapped OS error
    # We'll intentionally create a permission error by trying to write to a directory
    # that is not writable. On most systems, writing to root will fail; to keep this
    # example portable we instead simulate by opening a directory path for writing.
    try:
        # Open a directory path as a file to force a permission-like error
        bad_path = tmp_dir
        SafeTextFileWriter(bad_path, encoding="utf-8")
    except SplurgeSafeIoFilePermissionError as err:
        print("Caught mapped PermissionError -> SplurgeSafeIoFilePermissionError")
        print("original_exception:", repr(getattr(err, "original_exception", None)))
    except SplurgeSafeIoOsError as err:
        # Fallback: any other OS-level mapped error
        print("Caught other mapped OSError -> SplurgeSafeIoOsError")
        print("original_exception:", repr(getattr(err, "original_exception", None)))


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        print("Working directory:", tmp_dir)
        demo_path_validation(tmp_dir)
        demo_write_and_read(tmp_dir)
        demo_streaming(tmp_dir)
        demo_error_inspection(tmp_dir)


if __name__ == "__main__":
    main()
