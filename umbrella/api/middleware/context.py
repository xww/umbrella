'''
Created on 2012-10-23

@author: hzzhoushaoyu
'''

import webob.exc
import json

from umbrella.common import wsgi
import umbrella.common.log as logging
from umbrella.common import cfg
import umbrella.context

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

context_opts = [
    cfg.BoolOpt('owner_is_tenant', default=True),
    cfg.StrOpt('admin_role', default='admin'),
    cfg.BoolOpt('allow_anonymous_access', default=False),
    ]
CONF.register_opts(context_opts)


class ContextMiddleware(wsgi.Middleware):
    def process_response(self, resp):
            try:
                request_id = resp.request.context.request_id
                LOG.debug(_("req-%s is responsing") % request_id)
            except AttributeError:
                LOG.warn(_('Unable to retrieve request id from context'))
            else:
                resp.headers['x-openstack-request-id'] = 'req-%s' % request_id
            return resp

    def process_request(self, req):
        if req.headers.get('X-Auth-Token') is not None:
            kwargs = {'auth_tok': req.headers.get('X-Auth-Token')}
        else:
            kwargs = {}
        req.context = umbrella.context.RequestContext(**kwargs)


class AuthContextMiddleware(ContextMiddleware):
    def process_request(self, req):
        """Convert authentication information into a request context

        Generate a glance.context.RequestContext object from the available
        authentication headers and store on the 'context' attribute
        of the req object.

        :param req: wsgi request object that will be given the context object
        :raises webob.exc.HTTPUnauthorized: when value of the X-Identity-Status
                                            header is not 'Confirmed' and
                                            anonymous access is disallowed
        """
        if req.headers.get('X-Identity-Status') == 'Confirmed':
            req.context = self._get_authenticated_context(req)
        elif req.headers.get('X-Auth-Token') is not None:
            req.context = self._get_auth_token_context(req)
        elif CONF.allow_anonymous_access:
            req.context = self._get_anonymous_context()
        else:
            raise webob.exc.HTTPUnauthorized()

    def _get_anonymous_context(self):
        kwargs = {
            'user': None,
            'tenant': None,
            'roles': [],
            'is_admin': False,
            'read_only': True,
        }
        return umbrella.context.RequestContext(**kwargs)

    def _get_auth_token_context(self, req):
        return umbrella.context.RequestContext(
                auth_tok=req.headers.get('X-Auth-Token'))

    def _get_authenticated_context(self, req):
        #NOTE(bcwaldon): X-Roles is a csv string, but we need to parse
        # it into a list to be useful
        roles_header = req.headers.get('X-Roles', '')
        roles = [r.strip().lower() for r in roles_header.split(',')]

        #NOTE(bcwaldon): This header is deprecated in favor of X-Auth-Token
        deprecated_token = req.headers.get('X-Storage-Token')

        service_catalog = None
        if req.headers.get('X-Service-Catalog') is not None:
            try:
                catalog_header = req.headers.get('X-Service-Catalog')
                service_catalog = json.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError(
                    _('Invalid service catalog json.'))

        kwargs = {
            'user': req.headers.get('X-User-Id'),
            'tenant': req.headers.get('X-Tenant-Id'),
            'roles': roles,
            'is_admin': CONF.admin_role.strip().lower() in roles,
            'auth_tok': req.headers.get('X-Auth-Token', deprecated_token),
            'owner_is_tenant': CONF.owner_is_tenant,
            'service_catalog': service_catalog,
        }

        return umbrella.context.RequestContext(**kwargs)
