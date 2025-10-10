"""Trace SafeTextFileReader.read_as_stream internals for debugging.

This script re-implements the read_as_stream loop with verbose printing so
we can observe raw reads, decoder outputs, carry, parts, and chunk assembly.
Run after generating the sample CSV used in reproduction.
"""

import codecs
import re
from pathlib import Path

from splurge_safe_io.constants import MIN_BUFFER_SIZE

CSV_PATH = Path("tmp") / "large_clean.csv"


def trace(file_path: Path, buffer_size: int = MIN_BUFFER_SIZE, encoding: str = "utf-8"):
    decoder = codecs.getincrementaldecoder(encoding)()
    _newline_trail_re = re.compile(r"(?:\r\n|\r|\n|\x0b|\x0c|\x1c|\x1d|\x1e|\x85|\u2028|\u2029)+$")

    carry = ""
    chunk = []
    effective_chunk_size = 500

    with file_path.open("rb") as fh:
        read_no = 0
        while True:
            raw = fh.read(buffer_size)
            read_no += 1
            print(f"--- raw read #{read_no}: {len(raw)} bytes ---")
            if not raw:
                print("--- EOF raw read ---")
                break
            try:
                text = decoder.decode(raw)
            except Exception as e:
                print("Decoder error:", e)
                raise
            print(f"decoded text (len={len(text)}): {repr(text[:200])}...")

            working = carry + text
            parts = working.splitlines(True)
            print(f"parts ({len(parts)}): {[repr(p[:60]) for p in parts[:10]]} ...")

            if parts and _newline_trail_re.search(parts[-1]):
                new_carry = ""
            else:
                new_carry = parts.pop() if parts else ""
            print(f"carry before={repr(carry[:60])} new_carry={repr(new_carry[:60])}")

            for i, part in enumerate(parts):
                line = _newline_trail_re.sub("", part)
                print(f"  emit part #{i}: {repr(line)}")
                chunk.append(line)
                if len(chunk) >= effective_chunk_size:
                    print(f"  yielding chunk (size {len(chunk)})")
                    chunk = []

            carry = new_carry
            print(f"carry after loop: {repr(carry[:120])}\n")

        # Finalize
        remaining = decoder.decode(b"", final=True)
        print(f"final remaining (len={len(remaining)}): {repr(remaining[:200])}...")
        final_working = carry + remaining
        final_parts = final_working.splitlines(True) if final_working else []
        print(f"final_parts ({len(final_parts)}): {[repr(p[:60]) for p in final_parts[:10]]} ...")

        final_carry = ""
        if final_parts and _newline_trail_re.search(final_parts[-1]):
            final_carry = ""
        else:
            final_carry = final_parts.pop() if final_parts else ""

        for i, part in enumerate(final_parts):
            part_clean = _newline_trail_re.sub("", part)
            print(f"  final emit part #{i}: {repr(part_clean)}")
            chunk.append(part_clean)

        if final_carry:
            print(f"final carry to emit: {repr(final_carry)}")
            chunk.append(_newline_trail_re.sub("", final_carry))

        if chunk:
            print(f"final yielded chunk size: {len(chunk)}")


if __name__ == "__main__":
    if not CSV_PATH.exists():
        print("CSV not found at tmp/large_clean.csv — please run scripts/reproduce_issue_chunk_blank.py first")
        raise SystemExit(1)
    trace(CSV_PATH)
