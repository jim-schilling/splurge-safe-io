from splurge_safe_io import exceptions


def test_exception_hierarchy():
    # Basic existence and inheritance checks
    assert issubclass(exceptions.SplurgeSafeIoPathValidationError, exceptions.SplurgeSafeIoError)
    assert issubclass(exceptions.SplurgeSafeIoOSError, exceptions.SplurgeSafeIoError)
    assert issubclass(exceptions.SplurgeSafeIoValueError, exceptions.SplurgeSafeIoError)
    assert issubclass(exceptions.SplurgeSafeIoRuntimeError, exceptions.SplurgeSafeIoError)
    assert issubclass(exceptions.SplurgeSafeIoLookupError, exceptions.SplurgeSafeIoError)

    # Check specialized OS error subclasses
    assert issubclass(exceptions.SplurgeSafeIoFileNotFoundError, exceptions.SplurgeSafeIoOSError)
    assert issubclass(exceptions.SplurgeSafeIoPermissionError, exceptions.SplurgeSafeIoOSError)
    assert issubclass(exceptions.SplurgeSafeIoFileExistsError, exceptions.SplurgeSafeIoOSError)

    # Check Unicode error is a ValueError subclass
    assert issubclass(exceptions.SplurgeSafeIoUnicodeError, exceptions.SplurgeSafeIoValueError)


def test_exception_message_details():
    e = exceptions.SplurgeSafeIoError(error_code="general", message="msg", details={"key": "d"})
    assert e.message == "msg"
    assert e.details == {"key": "d"}


def test_file_not_found_error():
    """Test SplurgeSafeIoFileNotFoundError has error_code attribute."""
    exc = exceptions.SplurgeSafeIoFileNotFoundError(error_code="file-not-found", message="File not found")
    assert exc.error_code == "file-not-found"
    assert exc.message == "File not found"


def test_permission_error():
    """Test SplurgeSafeIoPermissionError has error_code attribute."""
    exc = exceptions.SplurgeSafeIoPermissionError(error_code="permission-denied", message="Permission denied")
    assert exc.error_code == "permission-denied"
    assert exc.message == "Permission denied"


def test_file_exists_error():
    """Test SplurgeSafeIoFileExistsError has error_code attribute."""
    exc = exceptions.SplurgeSafeIoFileExistsError(error_code="file-exists", message="File exists")
    assert exc.error_code == "file-exists"
    assert exc.message == "File exists"


def test_unicode_error():
    """Test SplurgeSafeIoUnicodeError has error_code attribute."""
    exc = exceptions.SplurgeSafeIoUnicodeError(error_code="decoding", message="Unicode decode error")
    assert exc.error_code == "decoding"
    assert exc.message == "Unicode decode error"
