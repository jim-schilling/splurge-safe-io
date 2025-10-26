from splurge_safe_io import exceptions


def test_exception_hierarchy():
    # Basic existence and inheritance checks)
    assert issubclass(exceptions.SplurgeSafeIoPathValidationError, exceptions.SplurgeSafeIoError)


def test_exception_message_details():
    e = exceptions.SplurgeSafeIoError(error_code="general", message="msg", details={"key": "d"})
    assert e.message == "msg"
    assert e.details == {"key": "d"}
