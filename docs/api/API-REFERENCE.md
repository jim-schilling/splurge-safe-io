# splurge-safe-io — API Reference

This document describes the public API for the `splurge_safe_io` package: its classes, functions, and exception contract.

## Public modules

- `splurge_safe_io.path_validator` — path validation helpers.
- `splurge_safe_io.safe_text_file_reader` — `SafeTextFileReader` and `open_safe_text_reader`.
- `splurge_safe_io.safe_text_file_writer` — `SafeTextFileWriter`, `open_safe_text_writer`, `TextFileWriteMode`.
- `splurge_safe_io.constants` — package default settings.
- `splurge_safe_io.exceptions` — library exceptions (see Exception Contract).

---

## Exceptions (summary)

All public APIs raise exceptions defined in `splurge_safe_io.exceptions`. Each exception is a subclass of `SplurgeSafeIoError` and includes:

- `message` (str): human-facing message
- `details` (str | None): optional diagnostic details
- `original_exception` (Exception | None): the original builtin exception if the library mapped from a builtin (populated when available)

### Principal error classes

- `SplurgeSafeIoError` — base class
- `SplurgeSafeIoFileOperationError` — base for file operation errors
  - `SplurgeSafeIoFileNotFoundError`
  - `SplurgeSafeIoFilePermissionError`
  - `SplurgeSafeIoFileDecodingError`
  - `SplurgeSafeIoFileEncodingError`
  - `SplurgeSafeIoFileAlreadyExistsError`
  - `SplurgeSafeIoStreamingError`
  - `SplurgeSafeIoOsError`
- `SplurgeSafeIoPathValidationError`
- `SplurgeSafeIoParameterError`
- `SplurgeSafeIoUnknownError`

See `splurge_safe_io.exceptions` for docstrings and hierarchy.

---

## Exception contract (mapping of builtins)

The library maps builtin/os-level exceptions to the small, stable set above. The mapping is deterministic and consistent across platforms:

- `FileNotFoundError` -> `SplurgeSafeIoFileNotFoundError`
- `PermissionError` -> `SplurgeSafeIoFilePermissionError`
- `UnicodeDecodeError` / `UnicodeError` -> `SplurgeSafeIoFileDecodingError`
- `UnicodeEncodeError` -> `SplurgeSafeIoFileEncodingError`
- `FileExistsError` -> `SplurgeSafeIoFileAlreadyExistsError`
- `OSError` (and `IOError` alias on modern Python) -> `SplurgeSafeIoOsError`
- Any other unexpected `Exception` -> `SplurgeSafeIoUnknownError`

Notes:
- All mapped exceptions preserve the original builtin via exception chaining (`raise ... from e`).
- The exception instance also includes the `original_exception` attribute for programmatic access. Prefer passing
    ``original_exception=<builtin-exc>`` to the exception constructor when raising; the library will also set
    ``__cause__`` via ``raise ... from e`` so both programmatic access and normal exception chaining are available.

---

## `splurge_safe_io.path_validator.PathValidator.validate_path`

Signature:

```
PathValidator.validate_path(
    file_path: str | Path,
    *,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_readable: bool = False,
    must_be_writable: bool = False,
    allow_relative: bool = True,
    base_directory: str | Path | None = None,
) -> pathlib.Path
```

Description: Validate a path for safety and platform correctness. Returns a resolved `Path` on success.

Raises:
- `SplurgeSafeIoPathValidationError` for validation failures
- `SplurgeSafeIoFileNotFoundError` when `must_exist=True` and file missing
- `SplurgeSafeIoFilePermissionError` when permissions checks fail

Example:

```py
from splurge_safe_io.path_validator import PathValidator

p = PathValidator.validate_path('/data/foo.txt', must_exist=True, must_be_file=True)
```

---

## `splurge_safe_io.safe_text_file_reader.SafeTextFileReader`

Constructor:
```
SafeTextFileReader(
    file_path: Path | str,
    *,
    encoding: str = 'utf-8',
    strip: bool = False,
    skip_header_lines: int = 0,
    skip_footer_lines: int = 0,
    chunk_size: int = 500,
    buffer_size: int = 8192,
)
```

Methods:
- `.read() -> list[str]`: Read full file and return normalized lines (LF newlines). Raises mapping exceptions above.
- `.preview(max_lines: int = 100) -> list[str]`: Return first N normalized lines.
- `.read_as_stream() -> Iterator[list[str]]`: Stream lists of lines (chunked). Uses an incremental decoder and yields lists containing up to `chunk_size` lines. The reader reads raw bytes from disk using a `buffer_size` (default 8192 bytes) per raw read; `chunk_size` controls the maximum number of lines returned per yielded list. If the incremental decoder raises `UnicodeError` (for example when decoding UTF-16 without a BOM), the implementation falls back to a full read and then yields chunked lists from the already-decoded lines.
- `.preview(max_lines: int = 100) -> list[str]`: Return first N normalized lines.
- `.read_as_stream() -> Iterator[list[str]]`: Stream lists of lines (chunked). Uses an incremental decoder and yields lists containing up to `chunk_size` lines. The reader reads raw bytes from disk using a `buffer_size` (default 8192 bytes) per raw read; `chunk_size` controls the maximum number of lines returned per yielded list. The implementation enforces a minimum buffer size (`MIN_BUFFER_SIZE = 4096`) — requests for a smaller `buffer_size` are rounded up to that minimum. If the incremental decoder raises `UnicodeError` (for example when decoding UTF-16 without a BOM), the implementation falls back to a full read and then yields chunked lists from the already-decoded lines.

Example:

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

r = SafeTextFileReader('data.txt', encoding='utf-8')
lines = r.read()
for chunk in r.read_as_stream():
    for ln in chunk:
        print(ln)
```

---

## `splurge_safe_io.safe_text_file_writer.SafeTextFileWriter`

Constructor:
```
SafeTextFileWriter(file_path: Path | str, *, file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE, encoding: str = 'utf-8', canonical_newline: str = '\n')
```

Methods:
- `.write(text: str) -> int`: Normalize newlines and write text.
- `.writelines(lines: Iterable[str]) -> None`
- `.flush() -> None`
- `.close() -> None`

Context manager helper:
- `open_safe_text_writer(file_path, *, encoding='utf-8', file_write_mode=TextFileWriteMode.CREATE_OR_TRUNCATE, canonical_newline='\n')` — yields an in-memory StringIO and writes normalized content to disk on successful exit.

Example:

```py
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

with open_safe_text_writer('out.txt') as buf:
    buf.write('one\r\ntwo\n')
```

---

## Versioning and changelog

Refer to `CHANGELOG.md` (if present) for details about changes.

---

## Notes for integrators

- Catch the small set of `SplurgeSafeIo*` exceptions rather than platform builtins to make code portable and stable across Python versions.
- If you need low-level details, inspect the `original_exception` attribute or `__cause__` on the exception instance.

---

For more examples and a detailed usage guide, see `README-DETAILS.md`.
