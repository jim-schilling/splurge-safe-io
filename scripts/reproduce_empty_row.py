"""Reproducer for empty-row issue in streaming reader.

This script writes a 10_000-line text file where each line is `Line {n}`
and then reads it back using SafeTextFileReader with buffer size set to
MIN_BUFFER_SIZE and chunk_size=100. It compares each read line to the
expected content and reports any mismatches, empty rows, or missing
lines.

Run from the project root: python scripts/reproduce_empty_row.py
"""

from pathlib import Path

from splurge_safe_io.constants import MIN_BUFFER_SIZE
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)
TEST_FILE = TMP_DIR / "reproduce_10000.txt"
NUM_LINES = 10_000
CHUNK_SIZE = 100


def write_test_file(path: Path, lines: int) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for i in range(1, lines + 1):
            fh.write(f"Line {i}\n")


def run_reproducer() -> None:
    print(f"Writing {NUM_LINES} lines to {TEST_FILE}")
    write_test_file(TEST_FILE, NUM_LINES)

    reader = SafeTextFileReader(TEST_FILE, buffer_size=MIN_BUFFER_SIZE, chunk_size=CHUNK_SIZE)

    expected_n = 1
    mismatches = 0
    empty_rows = 0
    total_read = 0

    for chunk_index, chunk in enumerate(reader.read_as_stream(), start=1):
        for line_index, line in enumerate(chunk, start=1):
            total_read += 1
            expected = f"Line {expected_n}"
            if line == "":
                empty_rows += 1
                print(f"Chunk {chunk_index} row {line_index}: EMPTY (expected: '{expected}')")
            if line != expected:
                mismatches += 1
                if mismatches <= 10:
                    print(f"Mismatch at overall #{total_read}: got: {repr(line)} expected: {repr(expected)}")
            expected_n += 1

    print(f"Done. total_read={total_read}, mismatches={mismatches}, empty_rows={empty_rows}")


if __name__ == "__main__":
    run_reproducer()
