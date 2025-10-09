from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def create_mixed_file(tmp_path, filename="mixed.txt"):
    p = tmp_path / filename
    # include different newline styles and multi-byte characters
    content = "line1\r\nline2\nline3\rline4 ü\nline5"
    p.write_bytes(content.encode("utf-8"))
    return p


def test_read_full_and_strip(tmp_path):
    p = create_mixed_file(tmp_path)
    r = SafeTextFileReader(p, strip=True)
    lines = r.read()
    assert lines[0] == "line1"
    assert any("ü" in ln for ln in lines)


def test_preview_limits(tmp_path):
    p = create_mixed_file(tmp_path)
    r = SafeTextFileReader(p)
    preview = r.preview(max_lines=2)
    assert len(preview) == 2


def test_streaming_with_chunks_and_footer(tmp_path):
    # create 10 lines
    p = tmp_path / "ten.txt"
    lines = [f"l{i}" for i in range(10)]
    p.write_text("\n".join(lines))

    # skip last 2 as footer, chunk size 3
    r = SafeTextFileReader(p, chunk_size=3, skip_footer_lines=2)
    out = []
    for chunk in r.read_as_stream():
        out.extend(chunk)
    # should have emitted 8 lines (10 - 2 footer)
    assert len(out) == 8
    assert out[-1] == "l7"


def test_streaming_header_skip(tmp_path):
    p = tmp_path / "h.txt"
    p.write_text("h1\nh2\nbody1\nbody2")
    r = SafeTextFileReader(p, skip_header_lines=2)
    all_lines = []
    for c in r.read_as_stream():
        all_lines.extend(c)
    assert all_lines == ["body1", "body2"]
