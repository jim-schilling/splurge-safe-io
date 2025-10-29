## Changelog

### [2025.4.1] - 2025-10-29

#### Updated
- Bump package version to `2025.4.1` in `pyproject.toml` and expose `__version__ = "2025.4.1"` in `splurge_safe_io/__init__.py`.
- Upgraded `splurge-exceptions` vendored code to latest version `2025.4.1` in `splurge_safe_io/_vendor/splurge_exceptions/` to incorporate recent fixes and improvements from the upstream package.

###  [2025.4.0] - 2025-10-29

#### Changed
- Bumped package version to `2025.4.0` in `pyproject.toml` and exposed `__version__ = "2025.4.0"` in `splurge_safe_io/__init__.py`.

#### Added
- Vendored `splurge-exceptions` package into `splurge_safe_io/_vendor/splurge_exceptions/` to reduce external dependencies and improve package stability.
- Added `cli.py` and `__main__.py` for command-line interface support, allowing users to run `python -m splurge_safe_io` to access package metadata and functionality.

#### Removed
- Removed dependency on `splurge-exceptions` package by vendoring necessary exception classes directly into `splurge_safe_io/_vendor/splurge_exceptions/`. This change simplifies dependency management and ensures tighter integration with the Splurge ecosystem.
- Updated all exception imports and references throughout the codebase to use the vendored exceptions instead of the external package.

### [2025.3.0] - 2025-10-27

#### Refactored/Fixed
- Refactored exception mapping in `SafeTextFileReader` and `SafeTextFileWriter` to ensure that all relevant built-in exceptions (including `OSError`, `PermissionError`, and `UnicodeError`) are correctly mapped to their corresponding `SplurgeSafeIo*` exceptions from the `splurge-exceptions` package.
- Updated unit and integration tests to cover the newly mapped exceptions, ensuring that all error branches are properly tested and validated.

#### Changed
- Bumped package version to `2025.3.0` in `pyproject.toml` and exposed `__version__ = "2025.3.0"` in `splurge_safe_io/__init__.py`.
- Updated development dependencies in `pyproject.toml` to latest compatible versions.

### [2025.2.1] - 2025-10-26

#### Changed
- Bump package version to `2025.2.1` in `pyproject.toml` and expose `__version__ = "2025.2.1"` in `splurge_safe_io/__init__.py`.
- Updated development dependencies in `pyproject.toml` to latest compatible versions.

### [2025.2.0] - 2025-10-25

#### Removed
- `PathValidator.validate_path()` has been removed. Users must now use `PathValidator.get_validated_path()` for all path validation needs.

#### Changed
- Updated documentation and examples to remove references to the deprecated `validate_path()` method.
- Bumped package version to `2025.2.0` in `pyproject.toml` and exposed `__version__ = "2025.2.0"` in `splurge_safe_io/__init__.py`.
- Updated development dependencies in `pyproject.toml` to latest compatible versions.
- Updated all exceptions to inherit from `SplurgeFrameworkError` from the `splurge-exceptions` package for better integration with the broader Splurge ecosystem.
- Exception signatures and behaviors have changed to reflect the new base class.

#### Added
- `open_safe_text_reader_as_stream()` function has been added to the public API in `splurge_safe_io/__init__.py` to allow users to easily access the streaming text file reader functionality.
- New unit tests to cover `open_safe_text_reader_as_stream()` functionality and ensure proper exception handling.

###  [2025.1.1] - 2025-10-17

#### Added
- New method `PathValidator.get_validated_path()` as a clearer and more explicit alternative to `PathValidator.validate_path()`. The new method has identical behavior but a more descriptive name.
- New `create_parents` parameter to `SafeTextFileWriter` constructor to optionally create parent directories if they do not exist when writing to a file. Defaults to `False` for backward compatibility.
- New unit tests to cover `PathValidator.get_validated_path()` and the `create_parents` functionality in `SafeTextFileWriter`.

#### Changed
- Updated `SafeTextFileReader` and `SafeTextFileWriter` to use `PathValidator.get_validated_path()` internally instead of `PathValidator.validate_path()`.
- Bumped package version to `2025.1.1` in `pyproject.toml` and exposed `__version__ = "2025.1.1"` in `splurge_safe_io/__init__.py`.
- Updated development dependencies in `pyproject.toml` to latest compatible versions.

#### Deprecated
- `PathValidator.validate_path()` is now deprecated and will be removed in a 2025.2.0 release. Users are encouraged to switch to `PathValidator.get_validated_path()` for all new code.

### [2025.1.0] - 2025-10-14

#### Removed
- `SafeTextFileReader.read_as_stream()` has been deleted.

#### Refactored
- `SafeTextFileReader.read()` now returns the normalized file contents as a single string.

#### Added
- More edge cases have been added to validate `SafeTextFileReader`:
   - Parameter Interaction
   - File Content
   - Streaming

#### Updated
- Many tests have been refactored to use `SafeTextFileReader.read()` for reading entire file contents
   - `SafeTextFileReader().read()` calls `SafeTextFileReader.readlines()` directly, so both methods are validated.

### [2025.0.6] - 2025-10-14

#### Added
- New methods `SafeTextFileReader.readlines()` and `SafeTextFileReader.readlines_as_stream()` to provide clearer API naming that matches Python's standard `file.readlines()` semantics.

#### Changed
- `SafeTextFileReader.read()` and `SafeTextFileReader.read_as_stream()` are now deprecated and will be removed in version 2025.1.0. Use `readlines()` and `readlines_as_stream()` instead.
- Updated documentation and examples to use the new preferred method names.
- In version 2025.1.0, `read()` will be repurposed to return the raw file content as a single string (matching Python's `file.read()` semantics).


### [2025.0.5] - 2025-10-13

#### Added
- Support for `skip_empty_lines` parameter in `SafeTextFileReader` to filter out whitespace-only lines during read operations.
- New unit tests to cover the behavior of `skip_empty_lines` in various methods (`read()`, `read_as_stream()`, `preview()`, and `line_count()`).
- Updated documentation in `docs/api/API-REFERENCE.md` to include `skip_empty_lines` parameter details and examples.

#### Documentation
- Added a short usage example to `docs/README-DETAILS.md` demonstrating `skip_empty_lines=True` with `read_as_stream()` and `preview()`.



### [2025.0.4] - 2025-10-10

#### Added
- `SafeTextFileReader.line_count()` — a memory-efficient helper to count logical lines. Uses a size threshold (default 64 MiB) to pick between a single full decode (small files) and the streaming reader (large files). The method intentionally ignores `skip_header_lines` and `skip_footer_lines` and validates that `threshold_bytes >= 1 MiB`.

#### Added / Changed
- Added and updated unit tests to cover `line_count()` behaviors for small and large files.
- Replaced fragile direct attribute assignment patterns in tests (for example, `Path.stat = ...`) with `monkeypatch.setattr(...)` to make tests robust and isolated.
- Resolved small lint and typing issues surfaced by `ruff` and `mypy` during development.


### [2025.0.3] - 2025-10-10
#### Changed
- `SafeTextFileReader.preview()` now uses the streaming reader internally and will stop reading as soon as the requested number of preview lines are available for most encodings. Encodings that cannot be decoded incrementally (for example certain UTF-16 variants without a BOM) still fall back to a full read.
- Default and minimum buffer sizes were increased to improve streaming throughput and reduce syscall overhead: `DEFAULT_BUFFER_SIZE` is now 32768 bytes and `MIN_BUFFER_SIZE` is now 16384 bytes.
- Default preview length changed from 100 to 25 lines (`DEFAULT_PREVIEW_LINES = 25`).

#### Added
- Unit tests covering preview streaming behavior, header/footer skipping in previews, encoding-fallback behavior, and ensuring the reader releases OS file handles when preview returns early.

#### Fixed
- Small lint/type issues surfaced by `ruff` and `mypy` were resolved.
- Updated docstrings and API reference to reflect the new defaults and streaming preview behavior.


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