"""Reproduce reported blank-line artifact when streaming clean CSV files.

This script creates a CSV with a header and 1000 non-empty rows and
iterates `SafeTextFileReader.read_as_stream()` using several combinations
of buffer_size and chunk_size to try to reproduce an empty-string row
emitted inside a chunk.

Run from project root: python scripts/reproduce_issue_chunk_blank.py
"""

from pathlib import Path

from splurge_safe_io.constants import DEFAULT_BUFFER_SIZE, MIN_BUFFER_SIZE
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

OUT_DIR = Path("tmp")
OUT_DIR.mkdir(exist_ok=True)
CSV_PATH = OUT_DIR / "large_clean.csv"


def write_csv(path: Path, rows: int = 1000) -> None:
    header = "id,name,value,description"
    lines = [header] + [f"{i},Item{i},Value{i},Description for item {i}" for i in range(rows)]
    path.write_text("\n".join(lines), encoding="utf-8")


def scan(reader: SafeTextFileReader):
    found = False
    for chunk_idx, chunk in enumerate(reader.read_as_stream(), start=1):
        blanks = [i for i, ln in enumerate(chunk) if ln == "" or (isinstance(ln, str) and ln.strip() == "")]
        if blanks:
            found = True
            print(
                f"=== Found blanks with buffer_size={reader.buffer_size} chunk_size={reader.chunk_size} strip={reader.strip} ==="
            )
            print(f"Chunk {chunk_idx}: len={len(chunk)} blanks_local_indices={blanks}")
            for idx in blanks[:5]:
                start = max(0, idx - 3)
                end = min(len(chunk), idx + 4)
                print(f"  sample around local index {idx} (chunk {chunk_idx}):")
                for j in range(start, end):
                    print(f"    {j}: {repr(chunk[j])}")
            print()
    return found


def main():
    write_csv(CSV_PATH, rows=1000)

    # Try combinations similar to the issue repro
    combos = [
        (MIN_BUFFER_SIZE, 500, True),
        (MIN_BUFFER_SIZE, 500, False),
        (DEFAULT_BUFFER_SIZE, 500, True),
        (DEFAULT_BUFFER_SIZE, 500, False),
    ]

    overall_found = False
    for buffer_size, chunk_size, strip in combos:
        reader = SafeTextFileReader(CSV_PATH, buffer_size=buffer_size, chunk_size=chunk_size, strip=strip)
        found = scan(reader)
        overall_found = overall_found or found

    if not overall_found:
        print("No blank-line artifacts detected for tried combos.")


if __name__ == "__main__":
    main()
