# -*- coding: utf-8 -*-
from time import time

from . import data_processing


def get_error(data):
    """ return the error if there is a corresponding exception """
    if isinstance(data, dict):
        if 'errors' in data:
            error = data['errors'][0]
        else:
            error = data.get('error', None)

        if isinstance(error, dict):
            if error.get('code') in errors:
                return error


async def throw(response, loads=None, encoding=None, **kwargs):
    """ Get the response data if possible and raise an exception """
    if loads is None:
        loads = data_processing.loads

    data = await data_processing.read(response, loads=loads,
                                      encoding=encoding)

    error = get_error(data)
    if error is not None:
        exception = errors[error['code']]
        raise exception(response=response, error=error, data=data, **kwargs)

    if response.status in statuses:
        exception = statuses[response.status]
        raise exception(response=response, data=data, **kwargs)

    # raise PeonyException if no specific exception was found
    raise PeonyException(response=response, data=data, **kwargs)


class PeonyException(Exception):
    """ Parent class of all the exceptions of Peony """

    def __init__(self, response=None, error=None, data=None, message=None):
        """
            Add the response and data attributes

        Extract message from the error if not explicitly given
        """
        self.response = response
        self.data = data
        self.error = error

        if not message:
            message = self.get_message()

        super().__init__(message)

    def get_message(self):
        if self.error is not None:
            return self.error.get('message', self.error)

        return str(self.data)

    @property
    def url(self):
        return self.response.url


class PeonyDecodeError(PeonyException):

    def __init__(self, exception, *args, **kwargs):
        self.exception = exception
        super().__init__(*args, **kwargs)

    def get_message(self):
        return "Could not decode response data:\n%s" % self.data


class MediaProcessingError(PeonyException):
    pass


class StreamLimit(PeonyException):
    pass


class ErrorDict(dict):
    """ A dict to easily add exception associated to a code """

    def code(self, code):
        """ Decorator to associate a code to an exception """
        def decorator(exception):
            self[code] = exception
            return exception

        return decorator


statuses = ErrorDict()
errors = ErrorDict()


@errors.code(32)
class NotAuthenticated(PeonyException):
    pass


@errors.code(34)
class DoesNotExist(PeonyException):

    def get_message(self):
        return super().get_message() + "\n(%s)" % self.url


@errors.code(64)
class AccountSuspended(PeonyException):
    pass


@errors.code(68)
class MigrateToNewAPI(PeonyException):
    pass


@errors.code(88)
class RateLimitExceeded(PeonyException):
    """ Exception raised on rate limit """

    @property
    def reset(self):
        """
            Time when the limit will be reset

        Returns
        -------
        int
            Time when the limit will be reset
        """
        return int(self.response.headers.get('X-Rate-Limit-Reset', 0))

    @property
    def reset_in(self):
        """
            Time in seconds until the limit will be reset

        Returns
        -------
        int
            Time in seconds until the limit will be reset
        """
        return max(self.reset - time(), 0)


@errors.code(92)
class SSLRequired(PeonyException):
    pass


@errors.code(130)
class OverCapacity(PeonyException):
    pass


@errors.code(131)
class InternalError(PeonyException):
    pass


@errors.code(135)
class CouldNotAuthenticate(PeonyException):
    pass


@errors.code(136)
class Blocked(PeonyException):
    pass


@errors.code(161)
class FollowLimit(PeonyException):
    pass


@errors.code(179)
class ProtectedTweet(PeonyException):
    pass


@errors.code(185)
class StatusLimit(PeonyException):
    pass


@errors.code(187)
class DuplicatedStatus(PeonyException):
    pass


@errors.code(215)
class BadAuthentication(PeonyException):
    pass


@errors.code(226)
class AutomatedRequest(PeonyException):
    pass


@errors.code(231)
class VerifyLogin(PeonyException):
    pass


@errors.code(251)
class RetiredEndpoint(PeonyException):
    pass


@errors.code(261)
class ReadOnlyApplication(PeonyException):
    pass


@errors.code(271)
class CannotMuteYourself(PeonyException):
    pass


@errors.code(272)
class NotMutingUser(PeonyException):
    pass


@errors.code(354)
class DMCharacterLimit(PeonyException):
    pass


@statuses.code(304)
class NotModified(PeonyException):
    pass


@statuses.code(400)
class BadRequest(PeonyException):
    pass


@statuses.code(401)
class Unauthorized(PeonyException):
    pass


@statuses.code(403)
class Forbidden(PeonyException):
    pass


@statuses.code(404)
class NotFound(PeonyException):

    def get_message(self):
        return super().get_message() + "\n(%s)" % self.url


@statuses.code(406)
class NotAcceptable(PeonyException):
    pass


@statuses.code(410)
class Gone(PeonyException):
    pass


@statuses.code(415)
class UnsupportedMediaType(PeonyException):
    pass


@statuses.code(420)
class EnhanceYourCalm(PeonyException):
    pass


@statuses.code(422)
class UnprocessableEntity(PeonyException):
    pass


@statuses.code(429)
class TooManyRequests(PeonyException):
    pass


@statuses.code(500)
class InternalServerError(PeonyException):
    pass


@statuses.code(502)
class BadGateway(PeonyException):
    pass


@statuses.code(503)
class ServiceUnavailable(PeonyException):
    pass


@statuses.code(504)
class GatewayTimeout(PeonyException):
    pass
