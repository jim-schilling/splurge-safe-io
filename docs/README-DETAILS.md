````markdown
# splurge-safe-io — Developer guide and extended examples

This guide complements the project `README.md` and the API reference (`docs/api/API-REFERENCE.md`) with
practical guidance, common workflows, and tips for integrating `splurge-safe-io` into applications.

Quick overview

- Purpose: deterministic, safe, and testable helpers for reading and writing text files.
- When to use: when you need consistent newline normalization, defensive path validation, or a memory-bounded
  streaming reader for large files.

Quick start (practical)

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

# Read a small file into memory
reader = SafeTextFileReader('example.txt')
lines = reader.read()

# Stream a large CSV in batches
reader = SafeTextFileReader('data/large.csv', chunk_size=500)
for batch in reader.read_as_stream():
    process_batch(batch)

# Write with normalized newlines
with open_safe_text_writer('out.txt', encoding='utf-8') as buf:
    buf.write('one\r\ntwo\n')
```

Streaming, buffers, and memory

- `read_as_stream()` is the streaming primitive. It reads raw bytes in `buffer_size` chunks and decodes via an
  incremental decoder, yielding lists of logical lines (up to `chunk_size` each).
- `buffer_size` controls the raw read granularity (default 32 KiB). The implementation enforces a reasonable
  minimum (`MIN_BUFFER_SIZE`), so requests for smaller buffers will be rounded up.
- Use streaming for large files or when you need bounded memory usage. Use `read()` for convenience with small files.

skip_empty_lines, header/footer, and strip — clear semantics

There are three independent controls you typically combine:

- `skip_header_lines` / `skip_footer_lines` — positional removal of the first/last N logical lines. These are applied
  first and preserve positional semantics (important for CSVs with footers/metadata).
- `skip_empty_lines` — boolean filter that removes whitespace-only lines (definition: `line.strip() == ""`). This is
  applied after header/footer skipping.
- `strip` — if True, all non-empty lines are `.strip()`'d before being returned.

Order of operations (important): header/footer -> skip_empty_lines filter -> strip. This ordering keeps header/footer
semantics intuitive while letting you filter and normalize the remaining content.

preview(max_lines) — efficient short reads

- `preview()` attempts to stop early: it uses the streaming path and yields the first `max_lines` lines (post-filtering).
- For encodings that don't support incremental decoding the reader will fall back to a full `read()` and then slice the
  first `max_lines` items. That fallback trades memory for correctness and is deterministic.

line_count(threshold_bytes=64*1024*1024)

- Purpose: count logical lines efficiently.
- Behavior: if the on-disk size is <= `threshold_bytes` the reader does a full decode and returns `len(lines)`. If larger,
  it streams with `read_as_stream()` and accumulates a counter to avoid building a full list.
- Guard: `threshold_bytes` must be >= 1 MiB. Passing a smaller value raises `SplurgeSafeIoParameterError`.
- Note: `line_count()` counts every logical line on disk; it intentionally does not apply `skip_header_lines` or
  `skip_footer_lines` — call `read()` and measure `len()` for filtered counts.

Encoding and incremental-decoder fallbacks

- Default encoding is UTF-8. The streaming reader uses `codecs.getincrementaldecoder(encoding)`.
- When the incremental decoder raises `UnicodeError` (for example with some UTF-16 files missing BOM), the reader falls
  back to `read()` and then yields chunked results. This keeps behavior correct at the cost of memory on that path.

Practical examples

1) Stream/process/write pipeline (memory-bounded):

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

reader = SafeTextFileReader('big.csv', chunk_size=1000)
with open_safe_text_writer('out.csv') as out_buf:
    for chunk in reader.read_as_stream():
        processed = [transform(ln) for ln in chunk]
        out_buf.writelines(processed)
```

2) Preview-first pipeline (cheap check before heavy processing):

```py
r = SafeTextFileReader('maybe-large.txt', skip_empty_lines=True)
snippet = r.preview(10)
if looks_like_csv(snippet):
    for chunk in r.read_as_stream():
        process(chunk)
```

3) Counting lines reliably for a very large file:

```py
r = SafeTextFileReader('huge.log')
total = r.line_count()  # streams if file > 64 MiB
```

Constants and tuning knobs

- `DEFAULT_BUFFER_SIZE` (32_768) — default raw read buffer size.
- `MIN_BUFFER_SIZE` (16_384) — enforced minimum for `buffer_size`.
- `DEFAULT_CHUNK_SIZE` (500) — default maximum lines per yielded chunk.
- `DEFAULT_PREVIEW_LINES` (25) — default for `preview()`.
- `DEFAULT_ENCODING` (`utf-8`) — default text encoding.

Troubleshooting & FAQs

- Q: "My `preview()` still read the whole file — why?"
  - If the encoding used cannot be decoded incrementally the reader will fall back to a full `read()`.
  - If you ask `preview()` for more lines than the file contains it'll read to EOF.

- Q: "Why did `line_count()` allocate lots of memory for a small file?"
  - `line_count()` uses a full decode for files smaller than `threshold_bytes`. For files with many multi-byte
    characters the decoded representation can be larger than the on-disk size.

- Q: "How can I get the number of lines after skipping header/footer?"
  - Call `read()` and compute `len(result)` with your `skip_*` and `skip_empty_lines` settings applied.

- Q: "Is newline normalization platform-independent?"
  - Yes — returned lines use `\n` as the canonical newline. Writers normalize newlines to the chosen canonical newline
    (default `\n`) when flushing to disk.

Where to look next

- API reference: `docs/api/API-REFERENCE.md` for canonical signatures.
- Tests: `tests/unit/test_safe_text_file_reader.py` for detailed behavior and encoding-fallback cases.
- CHANGELOG.md for release rationale and notable behavior changes.

````
