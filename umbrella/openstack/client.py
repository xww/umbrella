'''
Created on 2012-10-22

@author: hzzhoushaoyu
'''
import json

from umbrella.common import cfg
from umbrella.common import client
import umbrella.common.log as logging

LOG = logging.getLogger(__name__)

NOVA_OPTS = [
             cfg.StrOpt("nova_host", default="0.0.0.0"),
             cfg.IntOpt("nova_port", default=8774),
             cfg.StrOpt("nova_version", default="/v2")
]

GLANCE_OPTS = [
             cfg.StrOpt("glance_host", default="0.0.0.0"),
             cfg.IntOpt("glance_port", default=9292),
             cfg.StrOpt("glance_version", default="/v1")
]

KEYSTONE_OPTS = [
             cfg.StrOpt("keystone_host", default="0.0.0.0"),
             cfg.IntOpt("keystone_admin_port", default=35357),
             cfg.IntOpt("keystone_public_port", default=5000),
             cfg.StrOpt("keystone_version", default="/v2.0")
]

CONF = cfg.CONF
CONF.register_opts(NOVA_OPTS)
CONF.register_opts(GLANCE_OPTS)
CONF.register_opts(KEYSTONE_OPTS)


class BaseClient(client.BaseClient):
    """client base class for make request of other module"""

    def request(self, req):
        return self.response(req.method, req.path, params=req.params.mixed(),
                             headers=req.headers, body=req.body)

    def response(self, method, action, params={}, headers={}, body=None):
        LOG.debug(_("%(method)s %(action)s %(params)s %(headers)s"),
                                locals())
        res = self.do_request(method, action, params=params, headers=headers,
                              body=body)
        # Note(hzzhoushaoyu): if no json string in reponse body,
        # set data as response content
        resp_content = res.read()
        try:
            data = json.loads(resp_content)
        except ValueError:
            data = resp_content
        LOG.debug(_("response for %s %s successfully with %.100s... in body") %
                    (method, action, data))
        return data, res.getheaders()


class KeystoneAdminClient(BaseClient):

    def __init__(self, auth_tok=None, creds=None):
        host = CONF.keystone_host
        admin_port = CONF.keystone_admin_port
        doc_root = CONF.keystone_version
        super(KeystoneAdminClient, self).__init__(host=host, port=admin_port,
                doc_root=doc_root, auth_tok=auth_tok, creds=creds)


class KeystonePublicClient(BaseClient):

    def __init__(self, auth_tok=None, creds=None):
        host = CONF.keystone_host
        admin_port = CONF.keystone_public_port
        doc_root = CONF.keystone_version
        super(KeystonePublicClient, self).__init__(host=host, port=admin_port,
                doc_root=doc_root, auth_tok=auth_tok, creds=creds)


class GlanceClient(BaseClient):

    def __init__(self, auth_tok=None, creds=None):
        host = CONF.glance_host
        admin_port = CONF.glance_port
        doc_root = CONF.glance_version
        super(GlanceClient, self).__init__(host=host, port=admin_port,
                doc_root=doc_root, auth_tok=auth_tok, creds=creds)


class NovaClient(BaseClient):

    def __init__(self, auth_tok=None, creds=None):
        host = CONF.nova_host
        admin_port = CONF.nova_port
        doc_root = CONF.nova_version
        super(NovaClient, self).__init__(host=host, port=admin_port,
                doc_root=doc_root, auth_tok=auth_tok, creds=creds)
