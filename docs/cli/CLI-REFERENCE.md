# CLI Reference

The `splurge-safe-io` package provides a lightweight command-line interface (CLI) for accessing package metadata and utilities. This document describes all available CLI options and usage patterns.

## Overview

The CLI is designed to be minimal and focused. The primary use case is to display the installed package version and verify the installation is working correctly.

## Invoking the CLI

The CLI can be invoked in two ways:

### As a Module

```bash
python -m splurge_safe_io [OPTIONS]
```

### Using Entry Point (After Installation)

If you've installed the package via pip, you can run:

```bash
splurge-safe-io [OPTIONS]
```

> **Note:** The entry point name is `splurge-safe-io` (with hyphens), though the Python package name is `splurge_safe_io` (with underscores).

## Global Options

### `--version`

Display the installed package version and exit.

**Usage:**
```bash
python -m splurge_safe_io --version
```

**Output:**
```
splurge-safe-io 2025.4.0
```

### `--help`, `-h`

Display the help message with all available options.

**Usage:**
```bash
python -m splurge_safe_io --help
```

**Output:**
```
usage: splurge-safe-io [-h] [--version]

Splurge Safe IO - Python file I/O framework

options:
  -h, --help     show this help message and exit
  --version      show program's version number and exit
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - command executed without errors |
| `1` | Error - invalid arguments or unexpected failure |
| `2` | Argument error - incorrect or missing required arguments |

## Usage Examples

### Check Installation

Verify the package is installed and working:

```bash
$ python -m splurge_safe_io --version
splurge-safe-io 2025.4.0
```

### Display Help

Get a summary of available options:

```bash
$ python -m splurge_safe_io --help
usage: splurge-safe-io [-h] [--version]

Splurge Safe IO - Python file I/O framework

options:
  -h, --help     show this help message and exit
  --version      show program's version number and exit
```

### No Arguments (Show Help)

When invoked without arguments, the CLI displays help:

```bash
$ python -m splurge_safe_io
usage: splurge-safe-io [-h] [--version]

Splurge Safe IO - Python file I/O framework

options:
  -h, --help     show this help message and exit
  --version      show program's version number and exit
```

## Using the CLI in Scripts

### Bash/Shell Script

```bash
#!/bin/bash

# Check if the package is installed by verifying version
VERSION=$(python -m splurge_safe_io --version)
echo "Using $VERSION"

if [ $? -eq 0 ]; then
    echo "Package is properly installed"
else
    echo "Package installation failed"
    exit 1
fi
```

### Python Integration

If you need to check the version programmatically, use the Python API instead:

```python
import splurge_safe_io

print(f"Version: {splurge_safe_io.__version__}")
```

## Design Philosophy

The CLI is intentionally minimal because:

1. **Core functionality is in the Python API** - The library is designed for programmatic use in Python code, not shell scripting
2. **Lightweight and fast** - No heavy dependencies or initialization overhead
3. **Clear and focused** - Exposes only essential metadata

## Programmatic Usage

For programmatic use of the CLI, you can call the `main()` function directly:

```python
from splurge_safe_io.cli import main
import sys

# Run CLI and exit with its exit code
sys.exit(main(["--version"]))
```

Or pass arguments explicitly:

```python
from splurge_safe_io.cli import main

# Returns exit code directly
exit_code = main(["--help"])
```

## Future Extensibility

While the current CLI is minimal, the framework is designed to support future extensions:

- Additional subcommands could be added (e.g., `splurge-safe-io validate --path <path>`)
- Path validation utilities might be exposed as CLI tools
- File transformation or analysis tools could be added as future subcommands

For now, the primary interface remains the Python API as documented in [API-REFERENCE.md](../api/API-REFERENCE.md).

## Related Resources

- [API Reference](../api/API-REFERENCE.md) - Complete Python API documentation
- [README Details](../README-DETAILS.md) - Usage examples and guides
- [Examples](../../examples/) - Practical code examples
