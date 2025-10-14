"""Example: streaming read -> process -> write

This example demonstrates a memory-bounded pipeline that reads a file in chunks,
processes each chunk, and writes normalized output using the writer helper.

The `process_file` function is intentionally small and pure so it's easy to test.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer


def transform_line(line: str) -> str:
    """Simple transform: trim and uppercase the line for the example.

    Returns a string ending with the canonical newline ("\n").
    """
    return line.strip().upper() + "\n"


def process_file(
    src: Path | str,
    dst: Path | str,
    chunk_size: int = 500,
    transform: Callable[[str], str] | None = None,
    *,
    skip_empty_lines: bool = True,
) -> int:
    """Read `src` using streaming reader, transform and write to `dst`.

    Returns the number of logical lines written to `dst`.
    """
    transform = transform or transform_line
    reader = SafeTextFileReader(src, chunk_size=chunk_size, skip_empty_lines=skip_empty_lines)
    written = 0
    with open_safe_text_writer(dst, encoding="utf-8") as out_buf:
        for chunk in reader.readlines_as_stream():
            out_buf.writelines(transform(ln) for ln in chunk)
            written += len(chunk)
    return written


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stream/process/write example")
    parser.add_argument("src", help="Source text file")
    parser.add_argument("dst", help="Destination file")
    args = parser.parse_args()
    count = process_file(args.src, args.dst)
    print(f"wrote {count} lines to {args.dst}")
