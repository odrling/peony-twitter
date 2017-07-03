# -*- coding: utf-8 -*-
from time import time

from . import data_processing, utils


class BaseExceptionThrower:

    def __init__(self, response, encoding=None):
        self.response = response
        self.encoding = encoding

    async def read_data(self):
        return await self.response.read()

    async def raise_error(self, data):
        pass

    async def raise_status(self, data):
        if self.response.status in statuses:
            exception = statuses[self.response.status]
            raise exception(response=self.response, data=data)

    async def __call__(self):
        data = await utils.execute(self.read_data())
        await utils.execute(self.raise_error(data))
        await utils.execute(self.raise_status(data))
        raise PeonyException(response=self.response, data=data)


class PeonyExceptionThrower(BaseExceptionThrower):

    async def read_data(self):
        return await data_processing.read(self.response,
                                          encoding=self.encoding)

    @staticmethod
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

    async def raise_error(self, data):
        error = self.get_error(data)
        if error is not None:
            exception = errors[error['code']]
            raise exception(response=self.response, error=error, data=data)


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
        return super().get_message() + "\nurl: %s" % self.url


@statuses.code(405)
class MethodNotAllowed(PeonyException):
    pass


@statuses.code(406)
class NotAcceptable(PeonyException):
    pass


@statuses.code(407)
class ProxyAuthenticationRequired(PeonyException):
    pass


@statuses.code(408)
class RequestTimeout(PeonyException):
    pass


@statuses.code(409)
class Conflict(PeonyException):
    pass


@statuses.code(410)
class Gone(PeonyException):
    pass


@statuses.code(411)
class LengthRequired(PeonyException):
    pass


@statuses.code(412)
class PreconditionFailed(PeonyException):
    pass


@statuses.code(413)
class RequestEntityTooLarge(PeonyException):
    pass


@statuses.code(414)
class RequestURITooLong(PeonyException):
    pass


@statuses.code(415)
class UnsupportedMediaType(PeonyException):
    pass


@statuses.code(416)
class RequestedRangeNotSatisfiable(PeonyException):
    pass


@statuses.code(417)
class ExceptationFailed(PeonyException):
    pass


@statuses.code(418)
class ImATeapot(PeonyException):
    pass


@statuses.code(420)
class EnhanceYourCalm(PeonyException):
    pass


@statuses.code(421)
class MisdirectedRequest(PeonyException):
    pass


@statuses.code(422)
class UnprocessableEntity(PeonyException):
    pass


@statuses.code(423)
class Locked(PeonyException):
    pass


@statuses.code(424)
class FailedDependency(PeonyException):
    pass


@statuses.code(426)
class UpgradeRequired(PeonyException):
    pass


@statuses.code(428)
class PreconditionRequired(PeonyException):
    pass


@statuses.code(429)
class TooManyRequests(PeonyException):
    pass


@statuses.code(431)
class RequestHeaderFieldsTooLarge(PeonyException):
    pass


@statuses.code(451)
class UnavailableForLegalReasons(PeonyException):
    pass


@statuses.code(500)
class InternalServerError(PeonyException):
    pass


@statuses.code(501)
class NotImplemented(PeonyException):
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


@statuses.code(505)
class HTTPVersionNotSupported(PeonyException):
    pass


@statuses.code(506)
class VariantAlsoNegotiates(PeonyException):
    pass


@statuses.code(507)
class InsufficientStorage(PeonyException):
    pass


@statuses.code(508)
class LoopDetected(PeonyException):
    pass


@statuses.code(510)
class NotExtended(PeonyException):
    pass


@statuses.code(511)
class NetworkAuthenticationRequired(PeonyException):
    pass
