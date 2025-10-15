from pathlib import Path

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(data)


def test_streaming_footer_and_carry(tmp_path):
    # Create content where a multi-byte UTF-8 character splits across chunk boundary
    # We'll use an emoji (4 bytes in UTF-8) and set chunk_size small to force split.
    lines = ["line1", "line2", "emoji:\U0001f600", "line4", "line5"]
    text = "\n".join(lines) + "\n"
    data = text.encode("utf-8")
    p = tmp_path / "split.txt"
    write_bytes(p, data)

    reader = SafeTextFileReader(p, encoding="utf-8", strip=False, skip_footer_lines=2, chunk_size=10)
    emitted = []
    for chunk in reader.readlines_as_stream():
        for ln in chunk:
            emitted.append(ln)
    # The reader should skip the final footer lines. At minimum the
    # last line must not be emitted and the emoji line must be present.
    assert "line5" not in emitted
    assert "line1" in emitted
    assert "emoji:\U0001f600" in emitted


def test_streaming_header_and_final_carry(tmp_path):
    # Test header skipping with final carry (no trailing newline)
    lines = ["hdr1", "hdr2", "body1", "body2", "tail"]
    text = "\n".join(lines)  # no trailing newline
    p = tmp_path / "no_nl.txt"
    write_bytes(p, text.encode("utf-8"))

    reader = SafeTextFileReader(
        p, encoding="utf-8", strip=True, skip_header_lines=2, skip_footer_lines=1, chunk_size=50
    )
    all_lines = []
    for chunk in reader.readlines_as_stream():
        all_lines.extend(chunk)
    # After skipping 2 headers and 1 footer, left with body1 and body2
    assert all_lines == ["body1", "body2"]


def test_incremental_decoder_fallback_utf16_no_bom(tmp_path):
    # Create a UTF-16LE encoded file without BOM which triggers incremental decoder
    # to fail; ensure fallback to full-read occurs and we still get lines.
    lines = ["a", "b", "c"]
    text = "\n".join(lines) + "\n"
    data = text.encode("utf-16le")  # no BOM
    p = tmp_path / "utf16_nobom.txt"
    write_bytes(p, data)

    reader = SafeTextFileReader(
        p, encoding="utf-16", strip=False, skip_header_lines=0, skip_footer_lines=0, chunk_size=2
    )
    emitted = []
    for chunk in reader.readlines_as_stream():
        for ln in chunk:
            emitted.append(ln)
    assert emitted == lines
