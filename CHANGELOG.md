## Changelog

### [2025.0.1] - 2025-10-09


### [2025.0.0] - 2025-10-08
#### Added
- Initial release of splurge-safe-io package with:
    - SafeTextFileReader and SafeTextFileWriter for deterministic text file I/O with LF normalization.
    - PathValidator for secure path validation against traversal and dangerous characters.
    - Clear exception hierarchy mapping common I/O errors to package-specific exceptions.