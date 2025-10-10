## Changelog

### [2025.0.3] - 2025-10-10


### [2025.0.2] - 2025-10-09
#### Fixed
- Addressed an issue with buffer size calculation in `SafeTextFileReader` that could lead to incorrect line splitting. This fix prevents the reader from yielding empty string artifacts when reading files in chunks, ensuring that only actual lines from the source file are returned.
- Added unit tests to cover edge cases related to chunk boundaries and line splitting to prevent regression.

### [2025.0.1] - 2025-10-09
#### Changed
- Bump package version to `2025.0.1` in `pyproject.toml` and expose `__version__ = "2025.0.1"` in `splurge_safe_io/__init__.py`.
- `splurge_safe_io/__init__.py` now explicitly imports and re-exports package exception classes (removed any wildcard exception import) and tidied the public exports.
- `SafeTextFileReader` (`splurge_safe_io/safe_text_file_reader.py`):
    - Default for `strip` is now False.
    - Added a `buffer_size` constructor parameter and read-only `buffer_size` property (uses `DEFAULT_BUFFER_SIZE`/`MIN_BUFFER_SIZE` from constants).
    - Enforce a minimum raw-read buffer size using `MIN_BUFFER_SIZE`.
    - Fixed streaming implementation to use `buffer_size` for raw byte reads (previous behavior used the logical `chunk_size`).
    - Improved Google-style docstrings and added usage examples to clarify tuning `buffer_size` vs `chunk_size`.


### [2025.0.0] - 2025-10-08
#### Added
- Initial release of splurge-safe-io package with:
    - SafeTextFileReader and SafeTextFileWriter for deterministic text file I/O with LF normalization.
    - PathValidator for secure path validation against traversal and dangerous characters.
    - Clear exception hierarchy mapping common I/O errors to package-specific exceptions.