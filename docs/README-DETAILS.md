# splurge-safe-io — Developer guide and extended examples

## BREAKING CHANGES for v2025.2.0

> ⚠️ **`PathValidator.validate_path()` has been removed.** Use `PathValidator.get_validated_path()` instead. This change completes the API consolidation from v2025.1.0.
>
> ⚠️ **From v2025.1.0:** `SafeTextFileReader.read()` now returns a `str` containing the entire normalized file content instead of a `list[str]` of lines. Use `SafeTextFileReader.readlines()` to get a list of lines.

---

## Overview

This guide complements the project `README.md` and the API reference (`docs/api/API-REFERENCE.md`) with practical guidance, common workflows, and tips for integrating `splurge-safe-io` into applications.

**Purpose:** deterministic, safe, and testable helpers for reading and writing text files.

**When to use:**
- You need consistent newline normalization across platforms
- You need defensive path validation to prevent traversal attacks
- You need a memory-bounded streaming reader for large files
- You want reliable, semantic exception handling

---

## Core Features

### 1. **Deterministic Newline Normalization**
- All reads normalize to LF (`\n`), regardless of input encoding (CRLF, CR, LF)
- All writes normalize to a configurable canonical newline (default LF)
- Platform-independent behavior (Windows, macOS, Linux produce identical output)

### 2. **Memory-Efficient Streaming for Large Files**
- Stream text files in configurable chunks (default 500 lines)
- Control raw read buffer size (default 32 KiB, minimum 16 KiB)
- Process gigabyte+ files with bounded memory (O(chunk_size) not O(file_size))
- Incremental decoding with graceful fallback for problematic encodings

### 3. **Secure Path Validation**
- Prevent path traversal attacks (`..` sequences and absolute paths)
- Validate against dangerous characters per platform
- Optional policies: pre-resolution, post-resolution, validation, cleanup
- Detect file existence, type, and permissions (readable/writable)

### 4. **Clear, Semantic Exception Hierarchy**
- 6 core exception types (not dozens of builtin variants)
- Deterministic mapping from builtins to domain-specific exceptions
- Error codes for programmatic handling (e.g., "file-not-found", "encoding", "permission-denied", "general")
- Exception chaining preserves original error for debugging

### 5. **Flexible Text Processing Options**
- Skip header/footer lines by count
- Filter empty lines
- Strip whitespace from lines
- Configurable encoding (with incremental decoder fallback)

---

## Public API Summary

### Reader APIs

| API | Use Case | Memory | Notes |
|-----|----------|--------|-------|
| `SafeTextFileReader.read()` | Full file as single string | O(file_size) | Returns normalized `str` |
| `SafeTextFileReader.readlines()` | Full file as list of lines | O(file_size) | Returns `list[str]` with filters applied |
| `SafeTextFileReader.readlines_as_stream()` | Large files, batched processing | O(chunk_size) | Yields `list[str]` chunks |
| `SafeTextFileReader.preview(max_lines)` | Peek at first N lines | O(max_lines) | Early stop for most encodings |
| `SafeTextFileReader.line_count()` | Count logical lines | O(1) or O(file_size) | Efficient for large files |
| `open_safe_text_reader()` | Read context manager | O(file_size) | Convenience wrapper for `SafeTextFileReader` |
| `open_safe_text_reader_as_stream()` | Streaming context manager | O(chunk_size) | Convenience wrapper for `readlines_as_stream()` |

### Writer APIs

| API | Use Case | Notes |
|-----|----------|-------|
| `SafeTextFileWriter.write(text)` | Write text with newline normalization | Buffers in-memory until flush |
| `SafeTextFileWriter.writelines(lines)` | Write multiple lines | Normalizes each line |
| `SafeTextFileWriter.flush()` | Persist buffer to disk | Atomic write |
| `SafeTextFileWriter.close()` | Release resources | Auto-flushes |
| `open_safe_text_writer()` | Write context manager | Atomic: writes on success, discards on error |

### Path Validation APIs

| API | Use Case |
|-----|----------|
| `PathValidator.get_validated_path()` | Validate path safety and correctness |
| `PathValidator.register_pre_resolution_policy()` | Custom policy before path resolution |
| `PathValidator.register_post_resolution_policy()` | Custom policy after path resolution |
| `PathValidator.register_validation_policy()` | Custom validation checks |
| `PathValidator.register_cleanup_policy()` | Custom cleanup/audit policy |
| `PathValidator.clear_policies()` | Reset all registered policies |

### Exception Types

| Exception | Error Codes | Raised For |
|-----------|-------------|-----------|
| `SplurgeSafeIoError` | (base) | All splurge-safe-io errors |
| `SplurgeSafeIoOSError` | "general" | General OS-level file I/O errors |
| `SplurgeSafeIoFileNotFoundError` | "file-not-found" | File not found (subclass of `SplurgeSafeIoOSError`) |
| `SplurgeSafeIoPermissionError` | "permission-denied" | Permission denied (subclass of `SplurgeSafeIoOSError`) |
| `SplurgeSafeIoFileExistsError` | "file-exists" | File exists (subclass of `SplurgeSafeIoOSError`) |
| `SplurgeSafeIoValueError` | (various) | Invalid parameters |
| `SplurgeSafeIoUnicodeError` | "encoding", "decoding" | Unicode encoding/decoding errors (subclass of `SplurgeSafeIoValueError`) |
| `SplurgeSafeIoRuntimeError` | "general" | Unexpected runtime conditions |
| `SplurgeSafeIoLookupError` | "codecs-initialization" | Codec not found |
| `SplurgeSafeIoPathValidationError` | "path-traversal-detected" | Path validation failures |

---

## Quick Start Examples

### Basic Usage

```python
from splurge_safe_io import SafeTextFileReader, open_safe_text_writer

# Read a small file into memory
reader = SafeTextFileReader('example.txt')
lines = reader.readlines()  # Returns list[str]

# Stream a large CSV in batches
reader = SafeTextFileReader('data/large.csv', chunk_size=500)
for batch in reader.readlines_as_stream():
    process_batch(batch)

# Write with normalized newlines
with open_safe_text_writer('out.txt', encoding='utf-8') as buf:
    buf.write('one\r\ntwo\n')  # Normalized to one\ntwo\n on disk
```

### Path Validation

```python
from splurge_safe_io import PathValidator, SplurgeSafeIoPathValidationError

# Validate a path for safety and correctness
try:
    p = PathValidator.get_validated_path(
        '/data/file.txt',
        must_exist=True,
        must_be_readable=True
    )
except SplurgeSafeIoPathValidationError as e:
    print(f"Path validation failed: {e.message}")
```

### Streaming Context Manager

```python
from splurge_safe_io import open_safe_text_reader_as_stream

# Memory-efficient processing of huge file
with open_safe_text_reader_as_stream('huge.csv', chunk_size=1000) as reader:
    for chunk in reader:
        for line in chunk:
            process_csv_row(line)
```

### Filter and Transform

```python
from splurge_safe_io import SafeTextFileReader, open_safe_text_writer

reader = SafeTextFileReader(
    'messy.txt',
    skip_header_lines=1,      # Skip first line
    skip_empty_lines=True,     # Remove blank lines
    strip=True,                # Strip whitespace
    encoding='utf-8'
)

with open_safe_text_writer('clean.txt', create_parents=True) as out:
    for line in reader.readlines():
        if line.startswith('#'):
            continue
        out.write(f"PROCESSED: {line}\n")
```

### Exception Handling

The library provides a clear exception hierarchy for semantic error handling:

```python
from splurge_safe_io import (
    SafeTextFileReader,
    SplurgeSafeIoError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoUnicodeError,
    SplurgeSafeIoPathValidationError,
)

try:
    reader = SafeTextFileReader('data.txt', encoding='utf-8')
    lines = reader.readlines()
except SplurgeSafeIoFileNotFoundError as e:
    # Specific: file does not exist
    print(f"File not found: {e.message}")
except SplurgeSafeIoPermissionError as e:
    # Specific: permission denied
    print(f"Permission denied: {e.message}")
except SplurgeSafeIoUnicodeError as e:
    # Specific: encoding/decoding error
    print(f"Encoding error: {e.message}")
    # Access the original Python exception
    original = e.__cause__
except SplurgeSafeIoPathValidationError as e:
    # Specific: path validation failed
    print(f"Path validation failed: {e.error_code}")
except SplurgeSafeIoError as e:
    # Catch-all: any splurge-safe-io error
    print(f"IO error ({e.error_code}): {e.message}")
```

The exception hierarchy allows you to catch errors at different levels of specificity:

- **Broad catch:** `except SplurgeSafeIoError` catches all library errors
- **Category catch:** `except SplurgeSafeIoOSError` catches file I/O errors (including FileNotFoundError, PermissionError, FileExistsError)
- **Specific catch:** `except SplurgeSafeIoFileNotFoundError` catches only "file not found" errors

---

## Detailed Reference: Reader Configuration

### Streaming, Buffers, and Memory

- `readlines_as_stream()` is the streaming primitive. It reads raw bytes in `buffer_size` chunks and decodes via an
  incremental decoder, yielding lists of logical lines (up to `chunk_size` each).
- `buffer_size` controls the raw read granularity (default 32 KiB). The implementation enforces a reasonable
  minimum (`MIN_BUFFER_SIZE`), so requests for smaller buffers will be rounded up.
- Use streaming for large files or when you need bounded memory usage. Use `readlines()` for convenience with small files.

### skip_empty_lines, header/footer, and strip — Clear Semantics

There are three independent controls you typically combine:

- `skip_header_lines` / `skip_footer_lines` — positional removal of the first/last N logical lines. These are applied
  first and preserve positional semantics (important for CSVs with footers/metadata).
- `skip_empty_lines` — boolean filter that removes whitespace-only lines (definition: `line.strip() == ""`). This is
  applied after header/footer skipping.
- `strip` — if True, all non-empty lines are `.strip()`'d before being returned.

**Order of operations (important):** header/footer → skip_empty_lines filter → strip. This ordering keeps header/footer
semantics intuitive while letting you filter and normalize the remaining content.

### preview(max_lines) — Efficient Short Reads

- `preview()` attempts to stop early: it uses the streaming path and yields the first `max_lines` lines (post-filtering).
- For encodings that don't support incremental decoding the reader will fall back to a full `readlines()` and then slice the
  first `max_lines` items. That fallback trades memory for correctness and is deterministic.

### line_count(threshold_bytes=64*1024*1024)

- **Purpose:** count logical lines efficiently.
- **Behavior:** if the on-disk size is <= `threshold_bytes` the reader does a full decode and returns `len(lines)`. If larger,
  it streams with `readlines_as_stream()` and accumulates a counter to avoid building a full list.
- **Guard:** `threshold_bytes` must be >= 1 MiB. Passing a smaller value raises an error.
- **Note:** `line_count()` counts every logical line on disk; it intentionally does not apply `skip_header_lines` or
  `skip_footer_lines` — call `readlines()` and measure `len()` for filtered counts.

### Encoding and Incremental-Decoder Fallbacks

- Default encoding is UTF-8. The streaming reader uses `codecs.getincrementaldecoder(encoding)`.
- When the incremental decoder raises `UnicodeError` (for example with some UTF-16 files missing BOM), the reader falls
  back to `readlines()` and then yields chunked results. This keeps behavior correct at the cost of memory on that path.

---

## Practical Workflows

### 1. Stream/Process/Write Pipeline (Memory-Bounded)

```python
from splurge_safe_io import SafeTextFileReader, open_safe_text_writer

reader = SafeTextFileReader('big.csv', chunk_size=1000)
with open_safe_text_writer('out.csv', create_parents=True) as out_buf:
    for chunk in reader.readlines_as_stream():
        processed = [transform(ln) for ln in chunk]
        out_buf.writelines(processed)
```

### 2. Preview-First Pipeline (Cheap Check Before Heavy Processing)

```python
from splurge_safe_io import SafeTextFileReader

r = SafeTextFileReader('maybe-large.txt', skip_empty_lines=True)
snippet = r.preview(10)
if looks_like_csv(snippet):
    for chunk in r.readlines_as_stream():
        process(chunk)
```

### 3. Counting Lines Reliably for a Very Large File

```python
from splurge_safe_io import SafeTextFileReader

r = SafeTextFileReader('huge.log', encoding='utf-8')
total = r.line_count()  # streams if file > 64 MiB, efficient
```

### 4. Safe Path Handling with Policies

```python
from splurge_safe_io import PathValidator, SplurgeSafeIoPathValidationError

def audit_path(p):
    """Reject paths in temp directories."""
    if '/tmp/' in str(p) or '\\temp\\' in str(p).lower():
        raise SplurgeSafeIoPathValidationError(
            error_code="path-traversal-detected",
            message="Paths in temp directories are not allowed"
        )

PathValidator.register_post_resolution_policy(audit_path)

try:
    safe_path = PathValidator.get_validated_path('/var/log/app.log')
except SplurgeSafeIoPathValidationError:
    print("Path rejected by policy")
```

---

## Constants and Tuning Knobs

- `DEFAULT_BUFFER_SIZE` (32_768) — default raw read buffer size.
- `MIN_BUFFER_SIZE` (16_384) — enforced minimum for `buffer_size`.
- `DEFAULT_CHUNK_SIZE` (500) — default maximum lines per yielded chunk.
- `DEFAULT_PREVIEW_LINES` (25) — default for `preview()`.
- `DEFAULT_ENCODING` (`utf-8`) — default text encoding.
- `CANONICAL_NEWLINE` (`\n`) — canonical newline for normalization.

---

## Troubleshooting & FAQs

- **Q: "My `preview()` still read the whole file — why?"**
  - If the encoding used cannot be decoded incrementally the reader will fall back to a full `readlines()`.
  - If you ask `preview()` for more lines than the file contains it'll read to EOF.

- **Q: "Why did `line_count()` allocate lots of memory for a small file?"**
  - `line_count()` uses a full decode for files smaller than `threshold_bytes`. For files with many multi-byte
    characters the decoded representation can be larger than the on-disk size.

- **Q: "How can I get the number of lines after skipping header/footer?"**
  - Call `readlines()` and compute `len(result)` with your `skip_*` and `skip_empty_lines` settings applied.

- **Q: "Is newline normalization platform-independent?"**
  - Yes — returned lines use `\n` as the canonical newline. Writers normalize newlines to the chosen canonical newline
    (default `\n`) when flushing to disk.

- **Q: "How do I migrate from `validate_path()` to `get_validated_path()`?"**
  - The APIs are identical; simply replace `PathValidator.validate_path(...)` with `PathValidator.get_validated_path(...)`.
  - Both methods accept the same parameters and return a resolved `Path`.

---

## Where to Look Next

- **API Reference:** `docs/api/API-REFERENCE.md` for canonical signatures and detailed method documentation.
- **Tests:** `tests/unit/test_safe_text_file_reader.py` for detailed behavior and encoding-fallback cases.
- **Integration Tests:** `tests/integration/` for real-world scenarios and platform-specific behavior.
- **CHANGELOG.md:** for release rationale and notable behavior changes across versions.
