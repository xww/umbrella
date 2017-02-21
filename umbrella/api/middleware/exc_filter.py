# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011-2012 OpenStack LLC.
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

import webob.exc

from umbrella.common import wsgi
from umbrella.common import exception
import umbrella.common.log as logging

LOG = logging.getLogger(__name__)


class ExceptionMiddleware(wsgi.Middleware):

    @webob.dec.wsgify
    def __call__(self, req):
        try:
            response = self.process_request(req)
            if response:
                return response
            response = req.get_response(self.application)
            return self.process_response(response)
        except exception.AuthorizationFailure, e:
            msg = e.message
            LOG.debug(msg)
            raise webob.exc.HTTPUnauthorized(msg)
        except exception.AdminRequired, e:
            msg = e.message
            LOG.debug(msg)
            raise webob.exc.HTTPForbidden(msg)
        except exception.UmbrellaException, e:
            msg = e.message
            LOG.debug(msg)
            raise webob.exc.HTTPClientError(msg)
        except Exception, e:
            msg = str(e)
            LOG.exception(msg)
            raise webob.exc.HTTPServerError(str(e))
