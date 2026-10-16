from http import HTTPStatus


class BaseError(Exception):
    """Error with an HTTP status; translated to a response by base_error_handler."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(BaseError):
    status_code = HTTPStatus.NOT_FOUND


class UnprocessableError(BaseError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
