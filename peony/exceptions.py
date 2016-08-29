# -*- coding: utf-8 -*-
import time

from . import utils


def get_error(data):
    """ Get the error, this is quite a vertical code """
    if data is not None:
        if 'errors' in data:
            if data['errors']:
                return data['errors'][0]


async def throw(response, **kwargs):
    """ get the response data if possible and raise an exception """
    ctype = response.headers['CONTENT-TYPE'].lower()
    data = None

    if "json" in ctype:
        try:
            data = await response.json(loads=utils.loads)
        except:
            pass

    err = get_error(data)
    if err is not None:
        if 'code' in err:
            code = str(err['code'])
            if code in error:
                e = error[code]
                raise e(response=response, data=data, **kwargs)

    if str(response.status) in status:
        e = status[response.status]
        raise e(response=response, data=data, **kwargs)

    # raise PeonyException if no specific exception was found
    raise PeonyException(response=response, data=data, **kwargs)


class PeonyException(Exception):
    """ Parent class of all the exceptions of Peony """

    def __init__(self, response=None, data=None, message=None):
        """
            Add the response and data attributes

        Extract message from the error if not explicitly given
        """
        if not message:
            err = get_error(data)
            if err is not None:
                if 'message' in err:
                    message = err['message']

            message = message or str(response)

        self.response = response
        self.data = data

        super().__init__(message)


class MediaProcessingError(PeonyException):
    pass


class StreamLimit(PeonyException):
    pass


def convert_int_keys(func):
    def decorated(self, key, *args, **kwargs):
        if isinstance(key, int):  # convert int keys to str
            key = str(key)

        return func(self, key, *args, **kwargs)

    return decorated


class ErrorDict(dict):
    """ A dict to easily add exception associated to a code """

    @convert_int_keys
    def __getitem__(self, key):
        return super().__getitem__(key)

    @convert_int_keys
    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def code(self, code):
        def decorator(exception):
            self[code] = exception
            return exception

        return decorator


status = ErrorDict()
error = ErrorDict()


@error.code(32)
class NotAuthenticated(PeonyException):
    pass


@error.code(34)
class DoesNotExist(PeonyException):
    pass


@error.code(64)
class AccountSuspended(PeonyException):
    pass


@error.code(68)
class MigrateToNewAPI(PeonyException):
    pass


@error.code(88)
class RateLimitExceeded(PeonyException):

    @property
    def reset(self):
        return int(self.response.headers['X-Rate-Limit-Reset'])

    @property
    def reset_in(self):
        return self.reset - time.time()


@error.code(92)
class SSLRequired(PeonyException):
    pass


@error.code(130)
class OverCapacity(PeonyException):
    pass


@error.code(131)
class InternalError(PeonyException):
    pass


@error.code(135)
class CouldNotAuthenticate(PeonyException):
    pass


@error.code(136)
class Blocked(PeonyException):
    pass


@error.code(161)
class FollowLimit(PeonyException):
    pass


@error.code(179)
class ProtectedTweet(PeonyException):
    pass


@error.code(185)
class StatusLimit(PeonyException):
    pass


@error.code(187)
class DuplicatedStatus(PeonyException):
    pass


@error.code(215)
class BadAuthentication(PeonyException):
    pass


@error.code(226)
class AutomatedRequest(PeonyException):
    pass


@error.code(231)
class VerifyLogin(PeonyException):
    pass


@error.code(251)
class RetiredEndpoint(PeonyException):
    pass


@error.code(261)
class ReadOnlyApplication(PeonyException):
    pass


@error.code(271)
class CannotMuteYourself(PeonyException):
    pass


@error.code(272)
class NotMutingUser(PeonyException):
    pass


@error.code(354)
class DMCharacterLimit(PeonyException):
    pass


@status.code(304)
class NotModified(PeonyException):
    pass


@status.code(400)
class BadRequest(PeonyException):
    pass


@status.code(401)
class Unauthorized(PeonyException):
    pass


@status.code(403)
class Forbidden(PeonyException):
    pass


@status.code(404)
class NotFound(PeonyException):
    pass


@status.code(406)
class NotAcceptable(PeonyException):
    pass


@status.code(410)
class Gone(PeonyException):
    pass


@status.code(420)
class EnhanceYourCalm(PeonyException):
    pass


@status.code(422)
class UnprocessableEntity(PeonyException):
    pass


@status.code(429)
class TooManyRequests(PeonyException):
    pass


@status.code(500)
class InternalServerError(PeonyException):
    pass


@status.code(502)
class BadGateway(PeonyException):
    pass


@status.code(503)
class ServiceUnavailable(PeonyException):
    pass


@status.code(504)
class GatewayTimeout(PeonyException):
    pass
