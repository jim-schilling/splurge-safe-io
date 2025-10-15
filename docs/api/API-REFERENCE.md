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

### `splurge_safe_io.safe_text_file_reader.SafeTextFileReader`

Constructor:
```
SafeTextFileReader(
    file_path: Path | str,
    *,
    encoding: str = 'utf-8',
    strip: bool = False,
    skip_header_lines: int = 0,
    skip_footer_lines: int = 0,
    skip_empty_lines: bool = False,
    chunk_size: int = 500,
    buffer_size: int = 32768,
)
```
Arguments:
- `file_path (Path | str)`: Path to the file to read.
- `encoding (str)`: Text encoding for decoding. Defaults to 'utf-8'.
- `strip (bool)`: If True, strip leading/trailing whitespace from each line. Defaults to False.
- `skip_header_lines (int)`: Number of header lines to skip. Defaults to 0.
- `skip_footer_lines (int)`: Number of footer lines to skip. Defaults to 0.
- `skip_empty_lines (bool)`: Whether whitespace-only lines are removed from returned data. Defaults to False.
- `chunk_size (int)`: Maximum number of lines per yielded chunk in `readlines_as_stream()`. Defaults to 500.
- `buffer_size (int)`: Raw byte-read size used during streaming. Defaults to 32768 bytes.

Methods:
- `.read() -> str`: Read entire file and return normalized file content as a single string. Newline sequences are normalized to ``\n``. This is equivalent to calling `readlines()` and joining the result with ``\n``.
- `.readlines() -> list[str]`: Read full file and return normalized lines (LF newlines). Raises mapping exceptions above.
- `.readlines_as_stream() -> Iterator[list[str]]`: Stream lists of lines (chunked). Uses an incremental decoder and yields lists containing up to `chunk_size` lines. The reader reads raw bytes from disk using a `buffer_size` (default 32768 bytes) per raw read; `chunk_size` controls the maximum number of lines returned per yielded list. The implementation enforces a minimum buffer size (`MIN_BUFFER_SIZE = 16384`) — requests for a smaller `buffer_size` are rounded up to that minimum. If the incremental decoder raises `UnicodeError` (for example when decoding UTF-16 without a BOM), the implementation falls back to a full read and then yields chunked lists from the already-decoded lines.
- `.preview(max_lines: int = 25) -> list[str]`: Return first N normalized lines. `preview()` uses the streaming reader internally and will stop reading as soon as `max_lines` lines are available for most encodings; for encodings that do not support incremental decoding the implementation falls back to a full read.

- `.line_count(threshold_bytes: int = 64 * 1024 * 1024) -> int`: Count the number of logical lines in the file in a memory-efficient way.

    Description: This convenience method returns the total number of logical lines in the file. It intentionally ignores the instance-level `skip_header_lines` and `skip_footer_lines` settings and always counts every logical line on disk. To optimize for memory usage the implementation inspects the file size on disk:

    - If the on-disk file size is less than or equal to `threshold_bytes`, the method performs a single full decode using the reader's decoding rules and returns `len(lines)`.
    - If the on-disk file size is larger than `threshold_bytes`, the method reads the file using the streaming reader (`readlines_as_stream`) and accumulates the total line count without constructing a full in-memory list of all lines.

    Notes:
    - `threshold_bytes` defaults to 64 MiB. To avoid absurdly small thresholds the method requires `threshold_bytes >= 1 MiB` and will raise `SplurgeSafeIoParameterError` if a smaller value is passed.
    - The implementation does not attempt any byte-level fast-path optimizations; it relies on the existing decoding and streaming machinery and will therefore behave consistently with `readlines()` and `readlines_as_stream()` with respect to newline normalization and decoding errors.
    - If the streaming path encounters an incremental-decoder `UnicodeError`, it falls back to a full decode and returns the accurate line count.

    Example:

    ```py
    from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

    r = SafeTextFileReader('data.csv', encoding='utf-8')
    total = r.line_count()  # default threshold 64 MiB
    ```

Note: `skip_empty_lines` (bool) may be passed to the constructor and, when True,
causes the reader to filter out whitespace-only lines from `readlines()`,
`readlines_as_stream()`, `preview()` and `line_count()`.

Example:

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

# Read entire file as a single string
r = SafeTextFileReader('data.txt', encoding='utf-8')
content = r.read()  # Returns: "line1\nline2\nline3"

# Read as a list of lines
lines = r.readlines()  # Returns: ["line1", "line2", "line3"]

# Stream lines in chunks
for chunk in r.readlines_as_stream():
    for ln in chunk:
        print(ln)
```

---

### `splurge_safe_io.safe_text_file_writer.SafeTextFileWriter`

Constructor:
```
SafeTextFileWriter(
    file_path: Path | str, 
    *, 
    file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE, 
    encoding: str = 'utf-8', canonical_newline: str = '\n'
)
```
Arguments:
- `file_path (Path | str)`: Path to the file to write.
- `file_write_mode (TextFileWriteMode)`: Write mode (default CREATE_OR_TRUNCATE).
- `encoding (str)`: Text encoding for writing. Defaults to 'utf-8'.
- `canonical_newline (str)`: Newline to use when normalizing input. Defaults to '\n'.

Methods:
- `.write(text: str) -> int`: Normalize newlines and write text.
- `.writelines(lines: Iterable[str]) -> None`: Write multiple lines, normalizing newlines.
- `.flush() -> None`: Flush internal buffer to disk.
- `.close() -> None`: Close the writer and release any resources.

Context manager helper:
- `open_safe_text_writer(file_path, *, encoding='utf-8', file_write_mode=TextFileWriteMode.CREATE_OR_TRUNCATE, canonical_newline='\n')` — yields an in-memory StringIO and writes normalized content to disk on successful exit.

Example:

```py
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

with open_safe_text_writer('out.txt') as buf:
    buf.write('one\r\ntwo\n')
```

---

### `splurge_safe_io.path_validator.PathValidator`


Class/Static Methods:
- `PathValidator.register_pre_resolution_policy(policy: Callable[[str | Path], None]) -> None`: Register a pre-resolution policy function. The function is called with the raw input path before any resolution or validation. Raise `SplurgeSafeIoPathValidationError` to reject the path.
- `PathValidator.register_post_resolution_policy(policy: Callable[[Path], None]) -> None`: Register a post-resolution policy function. The function is called with the resolved path after validation. Raise `SplurgeSafeIoPathValidationError` to reject the path.
- `PathValidator.register_validation_policy(policy: Callable[[Path], None]) -> None`: Register a validation policy function. The function is called with the resolved path after validation. Raise `SplurgeSafeIoPathValidationError` to reject the path.
- `PathValidator.register_cleanup_policy(policy: Callable[[Path], None]) -> None`: Register a cleanup policy function. The function is called with the resolved path after all other processing. Raise `SplurgeSafeIoPathValidationError` to reject the path.
- `PathValidator.clear_policies() -> None`: Clear all registered policies.
- `PathValidator.get_registered_policies() -> dict[str, list[Callable]]`: Get a dictionary of registered policies by type.
- `PathValidator.validate_path(
    file_path: str | Path,
    *,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_readable: bool = False,
    must_be_writable: bool = False,
    allow_relative: bool = True,
    base_directory: str | Path | None = None,
) -> pathlib.Path`: Validate a path for safety and platform correctness. Returns a resolved `Path` on success.
`
- `PathValidator.sanitize_path(file_path: str | Path) -> str`: Sanitize a path string by removing dangerous characters. Returns the sanitized path string.
- `PathValidator.is_path_safe(file_path: str | Path) -> bool`: Check if a path string is safe (does not contain dangerous characters). Returns True if safe, False otherwise.

---

### `splurge_safe_io.constants`
- `DEFAULT_BUFFER_SIZE` (int): Default buffer size for raw byte reads in `SafeTextFileReader`. Default is 32_768 bytes.
- `MIN_BUFFER_SIZE` (int): Minimum buffer size for raw byte reads in `SafeTextFileReader`. Default is 16_384 bytes.
- `DEFAULT_PREVIEW_LINES` (int): Default number of lines to return in `SafeTextFileReader.preview()`. Default is 25 lines.
- `DEFAULT_CHUNK_SIZE` (int): Default chunk size for `SafeTextFileReader.readlines_as_stream()`. Default is 500 lines.
- `MIN_CHUNK_SIZE` (int): Minimum chunk size for `SafeTextFileReader.readlines_as_stream()`. Default is 10 lines.
- `DEFAULT_ENCODING` (str): Default text encoding. Default is 'utf-8'.
- `CANONICAL_NEWLINE` (str): Canonical newline character used for normalization. Default is '\n'.


### `splurge_safe_io.exceptions`
- `SplurgeSafeIoError` — base class for all splurge-safe-io exceptions.
- `SplurgeSafeIoFileOperationError` — base class for file operation errors.
    - `SplurgeSafeIoFileNotFoundError` — file not found.
    - `SplurgeSafeIoFilePermissionError` — permission denied.
    - `SplurgeSafeIoFileDecodingError` — decoding error.
    - `SplurgeSafeIoFileEncodingError` — encoding error.
    - `SplurgeSafeIoFileAlreadyExistsError` — file already exists.
    - `SplurgeSafeIoStreamingError` — streaming error.
    - `SplurgeSafeIoOsError` — generic OS error.
- `SplurgeSafeIoPathValidationError` — path validation error.
- `SplurgeSafeIoParameterError` — invalid parameter error.
- `SplurgeSafeIoUnknownError` — unknown error.

---

## Versioning and changelog

Refer to `CHANGELOG.md` (if present) for details about changes.

---

## Notes for integrators

- Catch the small set of `SplurgeSafeIo*` exceptions rather than platform builtins to make code portable and stable across Python versions.
- If you need low-level details, inspect the `original_exception` attribute or `__cause__` on the exception instance.

---

For more examples and a detailed usage guide, see `README-DETAILS.md`.
