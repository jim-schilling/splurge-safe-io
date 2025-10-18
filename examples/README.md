# Examples

This folder contains runnable example scripts demonstrating common usage of the `splurge_safe_io` package.

 `api_usage.py` — Comprehensive walkthrough of the public API:
   Path validation with `PathValidator.get_validated_path` (deprecated: `validate_path`)
  - Deterministic text writes with `open_safe_text_writer` / `SafeTextFileWriter`
  - Deterministic reads with `SafeTextFileReader` / `open_safe_text_reader`
  - Streaming reads using `read_as_stream()`
  - Exception mapping and inspection via the `original_exception` attribute and exception chaining (`from`)

How to run

From the repository root (make sure your venv is activated):

```bash
python examples/api_usage.py
```

The example uses a temporary directory and is safe to run locally.
