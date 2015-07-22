'''
Created on 2012-10-21

@author: hzzhoushaoyu
'''
from webob import exc

from umbrella.common import wsgi
from umbrella.openstack import client
import umbrella.common.log as logging

LOG = logging.getLogger(__name__)


class Controller():

    def keystone_admin_request(self, req):
        c = client.KeystoneAdminClient()
        result, headers = c.request(req)
        return result, headers

    def index(self, req):
        '''show all users in result'''
        result, headers = self.keystone_admin_request(req)
        return result

    def show(self, req, id):
        '''show user/tenant info by specified user/tenant id'''
        result, headers = self.keystone_admin_request(req)
        return result

    def delete_user(self, req, id):
        '''
        delete user or tenant by user/tenant id
        '''
        result, headers = self.keystone_admin_request(req)
        return result

    def _repack_user_data(self, value):
        try:
            user = value['user']
            extra = user.pop('extra')
            user.update(extra)
            return user
        except KeyError:
            LOG.exception(_("repack user data error."))
            raise exc.HTTPFailedDependency(_("Keystone method deprecated."))

    def set_password(self, req, user_id, body):
        '''
        set password for user whoes id is user_id
        '''
        result, headers = self.keystone_admin_request(req)
        # value that request successfully return will
        # actually contain user element with extra
        return self._repack_user_data(result)

    def update_user(self, req, user_id, body):
        '''
        enable or disable a user by content in body
        update user email
        '''
        result, headers = self.keystone_admin_request(req)
        return self._repack_user_data(result)


def create_resource():
    """Users resource factory method"""
    return wsgi.Resource(Controller())
