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

    def __init__(self, response=None, error=None, data=None, url=None,
                 message=None):
        """
            Add the response and data attributes

        Extract message from the error if not explicitly given
        """
        self.response = response
        self.data = data
        self.error = error
        self.url = url

        if not message:
            message = self.get_message()

        if url:
            message += "\nurl: " + url

        super().__init__(message)

    def get_message(self):
        if self.error is not None:
            return self.error.get('message', self.error)

        return str(self.data)


class PeonyUnavailableMethod(PeonyException):

    def __init__(self, message):
        super().__init__(message=message)


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


@statuses.code(304)
class HTTPNotModified(PeonyException):
    pass


@statuses.code(400)
class HTTPBadRequest(PeonyException):
    pass


@statuses.code(401)
class HTTPUnauthorized(PeonyException):
    pass


@statuses.code(403)
class HTTPForbidden(PeonyException):
    pass


@statuses.code(404)
class HTTPNotFound(PeonyException):
    pass


@statuses.code(406)
class HTTPNotAcceptable(PeonyException):
    pass


@statuses.code(409)
class HTTPConflict(PeonyException):
    pass


@statuses.code(410)
class HTTPGone(PeonyException):
    pass


@statuses.code(420)
class HTTPEnhanceYourCalm(PeonyException):
    pass


@statuses.code(422)
class HTTPUnprocessableEntity(PeonyException):
    pass


@statuses.code(429)
class HTTPTooManyRequests(PeonyException):
    pass


@statuses.code(500)
class HTTPInternalServerError(PeonyException):
    pass


@statuses.code(502)
class HTTPBadGateway(PeonyException):
    pass


@statuses.code(503)
class HTTPServiceUnavailable(PeonyException):
    pass


@statuses.code(504)
class HTTPGatewayTimeout(PeonyException):
    pass


@errors.code(3)
class InvalidCoordinates(HTTPBadRequest):
    pass


@errors.code(13)
class NoLocationAssociatedToIP(HTTPNotFound):
    pass


@errors.code(17)
class NoUserMatchesQuery(HTTPNotFound):
    pass


@errors.code(32)
class NotAuthenticated(HTTPUnauthorized):
    pass


@errors.code(34)
class DoesNotExist(HTTPNotFound):
    pass


@errors.code(36)
class CannotReportYourselfAsSpam(HTTPForbidden):
    pass


@errors.code(38)
class ParameterMissing(HTTPForbidden):
    pass


@errors.code(44)
class AttachmentURLInvalid(HTTPBadRequest):
    pass


@errors.code(50)
class UserNotFound(HTTPNotFound):
    pass


@errors.code(63)
class UserSuspended(HTTPNotFound):
    pass


@errors.code(64)
class AccountSuspended(HTTPForbidden):
    pass


@errors.code(68)
class MigrateToNewAPI(HTTPGone):
    pass


@errors.code(87)
class ActionNotPermitted(HTTPForbidden):
    pass


# TODO: check if that could be moved to RateLimitExceeded
@errors.code(88)
class RateLimitExceeded(HTTPTooManyRequests):
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


@errors.code(89)
class InvalidOrExpiredToken(HTTPForbidden):
    pass


@errors.code(92)
class SSLRequired(HTTPForbidden):
    pass


@errors.code(93)
class ApplicationNotAllowedToAccessDirectMessages(HTTPForbidden):
    pass


@errors.code(99)
class UnableToVerifyCredentials(HTTPForbidden):
    pass


@errors.code(120)
class ValueTooLong(HTTPForbidden):
    pass


@errors.code(130)
class OverCapacity(HTTPServiceUnavailable):
    pass


@errors.code(131)
class InternalError(HTTPInternalServerError):
    pass


@errors.code(136)
class Blocked(HTTPForbidden):
    pass


@errors.code(135)
class CouldNotAuthenticate(HTTPUnauthorized):
    pass


@errors.code(139)
class StatusAlreadyFavorited(HTTPForbidden):
    pass


@errors.code(144)
class StatusNotFound(HTTPNotFound):
    pass


@errors.code(150)
class CannotSendMessageToNonFollowers(HTTPForbidden):
    pass


@errors.code(160)
class FollowRequestAlreadyChanged(HTTPForbidden):
    pass


@errors.code(161)
class FollowLimit(HTTPForbidden):
    pass


@errors.code(162)
class FollowBlocked(HTTPForbidden):
    pass


@errors.code(179)
class ProtectedTweet(HTTPForbidden):
    pass


@errors.code(185)
class StatusLimit(HTTPForbidden):
    pass


@errors.code(186)
class TweetTooLong(HTTPForbidden):
    pass


@errors.code(187)
class DuplicatedStatus(HTTPForbidden):
    pass


@errors.code(205)
class SpamReportLimit(HTTPForbidden):
    pass


@errors.code(214)
class OwnerMustAllowDMFromAnyone(HTTPForbidden):
    pass


@errors.code(215)
class BadAuthentication(HTTPBadRequest):
    pass


@errors.code(220)
class AccessNotAllowedByCredentials(HTTPForbidden):
    pass


@errors.code(226)
class AutomatedRequest(HTTPForbidden):
    pass


@errors.code(251)
class RetiredEndpoint(HTTPGone):
    pass


@errors.code(261)
class ReadOnlyApplication(HTTPForbidden):
    pass


@errors.code(271)
class CannotMuteYourself(HTTPForbidden):
    pass


@errors.code(272)
class NotMutingUser(HTTPForbidden):
    pass


@errors.code(323)
class GIFNotAllowedWithMultipleImages(HTTPBadRequest):
    pass


@errors.code(324)
class MediaIDValidationFailed(HTTPBadRequest):
    pass


@errors.code(325)
class MediaIDNotFound(HTTPBadRequest):
    pass


@errors.code(326)
class AccountLocked(HTTPForbidden):
    pass


@errors.code(327)
class AlreadyRetweeted(HTTPForbidden):
    pass


@errors.code(349)
class CannotSendMessageToUser(HTTPForbidden):
    pass


@errors.code(354)
class DMCharacterLimit(HTTPForbidden):
    pass


@errors.code(355)
class SubscriptionAlreadyExists(HTTPConflict):
    pass


@errors.code(385)
class ReplyToUnavailableTweet(HTTPForbidden):
    pass


@errors.code(386)
class TooManyAttachmentTypes(HTTPForbidden):
    pass


@errors.code(407)
class InvalidURL(HTTPBadRequest):
    pass


@errors.code(415)
class CallbackURLNotApproved(HTTPForbidden):
    pass


@errors.code(416)
class InvalidOrSuspendedApplication(HTTPUnauthorized):
    pass


@errors.code(417)
class DesktopApplicationAuth(HTTPUnauthorized):
    pass


@errors.code(421)
class TweetNoLongerAvailable(HTTPNotFound):
    pass


@errors.code(422)
class TweetViolatedRules(TweetNoLongerAvailable):
    pass


@errors.code(433)
class TweetIsReplyRestricted(HTTPForbidden):
    pass
