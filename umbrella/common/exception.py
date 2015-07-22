# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Umbrella exception subclasses"""
import urlparse


class RedirectException(Exception):
    def __init__(self, url):
        self.url = urlparse.urlparse(url)


class UmbrellaException(Exception):
    """
    Base Umbrella Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred")

    def __init__(self, message=None, *args, **kwargs):
        if not message:
            message = self.message
        try:
            message = message % kwargs
            self.message = message
        except Exception:
            # at least get the core message out if something happened
            pass
        super(UmbrellaException, self).__init__(message)


class MissingArgumentError(UmbrellaException):
    message = _("Missing required argument.")


class MissingCredentialError(UmbrellaException):
    message = _("Missing required credential: %(required)s")


class BadAuthStrategy(UmbrellaException):
    message = _("Incorrect auth strategy, expected \"%(expected)s\" but "
                "received \"%(received)s\"")


class NotFound(UmbrellaException):
    message = _("An object with the specified identifier was not found.")


class AuthBadRequest(UmbrellaException):
    message = _("Connect error/bad request to Auth service at URL %(url)s.")


class AuthUrlNotFound(UmbrellaException):
    message = _("Auth service at URL %(url)s not found.")


class AuthorizationFailure(UmbrellaException):
    message = _("Authorization failed.")


class NotAuthenticated(UmbrellaException):
    message = _("You are not authenticated.")


class AdminRequired(NotAuthenticated):
    message = _("User does not have admin privileges")


class Forbidden(UmbrellaException):
    message = _("You are not authorized to complete this action.")


class Invalid(UmbrellaException):
    message = _("Data supplied was not valid.")


class WorkerCreationFailure(UmbrellaException):
    message = _("Server worker creation failed: %(reason)s.")


class InvalidContentType(UmbrellaException):
    message = _("Invalid content type %(content_type)s")


class Duplicate(UmbrellaException):
    message = _("An object with the same identifier already exists.")


class MultipleChoices(UmbrellaException):
    message = _("The request returned a 302 Multiple Choices. This generally "
                "means that you have not included a version indicator in a "
                "request URI.\n\nThe body of response returned:\n%(body)s")


class LimitExceeded(UmbrellaException):
    message = _("The request returned a 413 Request Entity Too Large. This "
                "generally means that rate limiting or a quota threshold was "
                "breached.\n\nThe response body:\n%(body)s")

    def __init__(self, *args, **kwargs):
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)
        super(LimitExceeded, self).__init__(*args, **kwargs)


class ServerError(UmbrellaException):
    message = _("The request returned 500 Internal Server Error.")


class ServiceUnavailable(UmbrellaException):
    message = _("The request returned 503 Service Unavilable. This "
                "generally occurs on service overload or other transient "
                "outage.")

    def __init__(self, *args, **kwargs):
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)
        super(ServiceUnavailable, self).__init__(*args, **kwargs)


class Unimplementation(ServiceUnavailable):
    message = _("The method NOT implements yet.")


class UnexpectedStatus(UmbrellaException):
    message = _("The request returned an unexpected status: %(status)s."
                "\n\nThe response body:\n%(body)s")


class ClientConnectionError(UmbrellaException):
    message = _("There was an error connecting to a server")


class InvalidRedirect(UmbrellaException):
    message = _("Received invalid HTTP redirect.")


class MaxRedirectsExceeded(UmbrellaException):
    message = _("Maximum redirects (%(redirects)s) was exceeded.")


class RegionAmbiguity(UmbrellaException):
    message = _("Multiple 'image' service matches for region %(region)s. This "
                "generally means that a region is required and you have not "
                "supplied one.")


class NoServiceEndpoint(UmbrellaException):
    message = _("Response from Keystone does not contain a Glance endpoint.")


class AuthorizationRedirect(UmbrellaException):
    message = _("Redirecting to %(uri)s for authorization.")


class DatabaseMigrationError(UmbrellaException):
    message = _("There was an error migrating the database.")


class InvalidSortKey(Invalid):
    message = _("Sort key supplied was not valid.")


class InvalidIP(Invalid):
    message = _("Format of IP supplied was not valid.")


class InvalidFilterItem(Invalid):
    message = _("Sort key supplied was not valid.")


class InvalidFilterRangeValue(Invalid):
    message = _("Unable to filter using the specified range.")


class UnableUpdateValue(Invalid):
    message = _("Unable to update the specified value.")
