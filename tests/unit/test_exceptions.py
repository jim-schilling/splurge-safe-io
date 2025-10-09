from splurge_safe_io import exceptions


def test_exception_hierarchy():
    # Basic existence and inheritance checks
    assert issubclass(exceptions.SplurgeSafeIoFileNotFoundError, exceptions.SplurgeSafeIoFileOperationError)
    assert issubclass(exceptions.SplurgeSafeIoPathValidationError, exceptions.SplurgeSafeIoValidationError)
    assert issubclass(exceptions.SplurgeSafeIoParameterError, exceptions.SplurgeSafeIoValidationError)


def test_exception_message_details():
    e = exceptions.SplurgeSafeIoError("msg", details="d")
    assert e.message == "msg"
    assert e.details == "d"
