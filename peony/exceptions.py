# -*- coding: utf-8 -*-
import time
from functools import wraps

from . import utils


def _get_error(data):
    """ Get the error, this is quite a vertical code """
    if data is not None:
        if 'errors' in data:
            if data['errors']:
                return data['errors'][0]


async def throw(response, **kwargs):
    """ Get the response data if possible and raise an exception """
    ctype = response.headers['CONTENT-TYPE'].lower()
    data = None

    if "json" in ctype:
        try:
            data = await response.json(loads=utils.loads)
        except:
            pass

    err = _get_error(data)
    if err is not None:
        if 'code' in err:
            code = str(err['code'])
            if code in errors:
                exception = errors[code]
                raise exception(response=response, data=data, **kwargs)

    if str(response.status) in statuses:
        exception = statuses[response.status]
        raise exception(response=response, data=data, **kwargs)

    # raise PeonyException if no specific exception was found
    raise PeonyException(response=response, data=data, **kwargs)


class PeonyException(Exception):
    """ Parent class of all the exceptions of Peony """

    def __init__(self, response=None, data=None, message=None):
        """
            Add the response and data attributes

        Extract message from the error if not explicitly given
        """
        self.response = response
        self.data = data

        if not message:
            message = self.get_message()

        super().__init__(message)

    def get_message(self):
        err = _get_error(self.data)
        if err is not None:
            if 'message' in err:
                message = err['message']

        return message or str(self.response)

class MediaProcessingError(PeonyException):
    pass


class StreamLimit(PeonyException):
    pass


def _convert_int_keys(func):
    """ convert input keys to str """
    @wraps(func)
    def decorated(self, key, *args, **kwargs):
        if isinstance(key, int):  # convert int keys to str
            key = str(key)

        return func(self, key, *args, **kwargs)

    return decorated


class ErrorDict(dict):
    """ A dict to easily add exception associated to a code """

    @_convert_int_keys
    def __getitem__(self, key):
        return super().__getitem__(key)

    @_convert_int_keys
    def __setitem__(self, key, value):
        super().__setitem__(key, value)

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

    @property
    def url(self):
        return self.response.url

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
        return int(self.response.headers['X-Rate-Limit-Reset'])

    @property
    def reset_in(self):
        """
            Time in seconds until the limit will be reset

        Returns
        -------
        int
            Time in seconds until the limit will be reset
        """
        return self.reset - time.time()


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
    pass


@statuses.code(406)
class NotAcceptable(PeonyException):
    pass


@statuses.code(410)
class Gone(PeonyException):
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
