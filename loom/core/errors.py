class LoomException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ToolNotFoundError(LoomException):
    pass


class ToolValidationError(LoomException):
    pass


class PermissionDeniedError(LoomException):
    pass


class ToolExecutionTimeout(LoomException):
    pass


class ExecutionAbortedError(LoomException):
    pass

