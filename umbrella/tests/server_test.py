# Created on 2013-6-26
#
#@author:hzrandd

import mox

from umbrella.api.list_operation import filter as list_filter
from umbrella.api import server
from umbrella.openstack import api as ops_api
from umbrella.openstack import client
from umbrella.tests import base


class ControllerTest(base.IsolatedUnitTest):

    def test_list_flavor_key_id(self):
        expect = {
            '1':
            {'nbs': 1,
             'vcpus': 1,
             'ephemeral_gb': 0,
             'ecu': 1,
             'memory': 512
             }
        }
        flavors = {
            'flavors':
                  [{
                   'name': 'flavor_01',
                   'ram': 512,
                   'OS-FLV-EXT-DATA:ephemeral':0, 'vcpus': 1,
                   'extra_specs': {u'ecus_per_vcpu:': u'1', u'nbs': u'ture'},
                   'os-flavor-access:is_public': True, 'id': '1'
                  }
                  ]
        }
        req = 'fake-req'
        tenant_id = 'fake_tanant_id'
        flavor_id = 'fake_flavor_id'

        def fake_get_map_flavor(self, req, tenant_id, flavor_id):
            return flavors

        self.stubs.Set(server.Controller, '_get_map_flavor',
                       fake_get_map_flavor)

        controll = server.Controller()
        re = controll.list_flavor_key_id(req, tenant_id, flavor_id)
        self.assertEqual(re, expect)

    def test_list_flavor_key_info(self):
        expect = {'1_1_512_0_1': 1}
        flavors = {
            'flavors':
                  [
                      {'name': 'flavor_01',
                       'ram': 512,
                       'OS-FLV-EXT-DATA:ephemeral':0, 'vcpus': 1,
                       'extra_specs':
                       {u'ecus_per_vcpu:': u'1', u'nbs': u'ture'},
                       'os-flavor-access:is_public': False, 'id': '1'
                       }
                  ]
        }
        req = 'fake-req'
        tenant_id = 'fake_tanant_id'
        flavor_id = 'fake_flavor_id'

        def fake_get_map_flavor(self, req, tenant_id, flavor_id):
            return flavors

        self.stubs.Set(server.Controller, '_get_map_flavor',
                       fake_get_map_flavor)

        controll = server.Controller()
        re = controll.list_flavor_key_info(req, tenant_id, flavor_id)
        self.assertEqual(re, expect)

    def test_get_map_flavor(self):
        flavors = {
            'flavors':
                 [
                     {'name': 'flavor_01', 'ram': 512,
                      'OS-FLV-EXT-DATA:ephemeral':0, 'vcpus': 1,
                      'extra_specs':
                      {u'ecus_per_vcpu:': u'1', u'nbs': u'ture'},
                      'os-flavor-access:is_public': True, 'id': '1'
                      }
                 ]
        }
        expect = {
            'flavors':
            [
                {'name': 'flavor_01',
                 'ram': 512, 'vcpus': 1,
                 'extra_specs': {u'nbs': u'ture', u'ecus_per_vcpu:': u'1'},
                 'os-flavor-access:is_public': True,
                 'OS-FLV-EXT-DATA:ephemeral': 0, 'id': '1'
                 }
            ]
        }
        tenant_id = 'fake_tanant_id'
        flavor_id = 'fake_flavor_id'

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}

        ign_var = mox.IgnoreArg()
        m.StubOutWithMock(client.BaseClient, 'response')
        client.BaseClient.response(ign_var, ign_var, headers=ign_var,
                                   params=ign_var).AndReturn((flavors, ''))
        m.ReplayAll()

        controll = server.Controller()
        re = controll._get_map_flavor(mock, tenant_id, flavor_id)
        self.assertEqual(re, expect)
        m.VerifyAll()

    def test_is_flavor_for_creating_passed(self):
        expect = True
        flavor_name = {'name': 'flavor_01'}

        re = server._is_flavor_for_creating(flavor_name)
        self.assertEqual(re, expect)

    def test_is_flavor_for_creating_failed(self):
        expect = False
        flavor_name = {'name': 'm1.small'}

        re = server._is_flavor_for_creating(flavor_name)
        self.assertEqual(re, expect)

    def test_list_all_quotas(self):
        expect = {
            'quotas': [
                {'ecus': {'reserved': 0,
                          'limit': 20,
                          'in_use': 5},
                 'tenant_name': 'Project_admin',
                 'ram': {'reserved': 0.0,
                         'limit': 50.0,
                         'in_use': 4.04},
                 'volumes': {'reserved': 0,
                             'limit': 10,
                             'in_use': 0},
                 'tenant_id': '5dd12337fcaf45a99269053caa8549f2',
                 'cores': {'reserved': 0,
                           'limit': 20,
                           'in_use': 11},
                 'local_gb': {'reserved': 0,
                              'limit': 1000,
                              'in_use': 20}
                 }
            ]
        }
        result = {
            '5dd12337fcaf45a99269053caa8549f2':
            {
                'cores': {'in_use': 1, 'limit': 20, 'reserved': 0},
                'ecus': {'in_use': 5, 'limit': 20, 'reserved': 0},
                'local_gb': {'in_use': 20, 'limit': 1000, 'reserved': 0},
                'ram': {'in_use': 4136, 'limit': 51200, 'reserved': 0},
                'volumes': {'in_use': 0, 'limit': 10, 'reserved': 0}
            }
        }
        filter_result = [
            {'cores':
             {'in_use': 11, 'limit': 20, 'reserved': 0},
             'ecus': {'in_use': 5, 'limit': 20, 'reserved': 0},
             'local_gb': {'in_use': 20, 'limit': 1000, 'reserved': 0},
             'ram': {'in_use': 4136, 'limit': 51200, 'reserved': 0},
             'tenant_id': '5dd12337fcaf45a99269053caa8549f2',
             'tenant_name': 'Project_admin',
             'volumes': {'in_use': 0, 'limit': 10, 'reserved': 0}
             }
        ]
        keypairs = []
        tenant = {'id': '5dd12337fcaf45a99269053caa8549f2', 'enabled': True,
                  'description': None, 'name': 'Project_admin'}
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'
        user_info = {'id': '5dd12337fcaf45a99269053caa8549f2', 'enabled': True,
                     'description': None, 'name': 'Project_admin',
                     'tenantName': 'test1',
                     'email': 'hzrandd@corp.netease.com'}
        headers = ''

        def fake_nova_request(self, req):
            return result, headers

        def fake_get_keypairs(tenant_id, auth_token):
            return keypairs

        def fake_get_user(userid, auth_token):
            return user_info

        def fake_get_tenant(tenantid, auth_token):
            return tenant

        def fake_filter_quotas(req, tenant_id, converted_result):
            return filter_result

        self.stubs.Set(server.Controller, '_nova_request', fake_nova_request)
        self.stubs.Set(ops_api, 'get_keypairs', fake_get_keypairs)
        self.stubs.Set(ops_api, 'get_user', fake_get_user)
        self.stubs.Set(ops_api, 'get_tenant', fake_get_tenant)
        self.stubs.Set(list_filter, 'filter_quotas', fake_filter_quotas)

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}
        mock.GET = ''

        controll = server.Controller()
        re = controll.list_all_quotas(mock, tenant_id)
        self.assertEqual(re, expect)

    def test_list_all_quotas_filter_out_tenant(self):
        # Note(hzrandd):set tenant_id = '',test filter out the empty tenant id.
        expect = {'quotas': []}
        result = {
            '': {
                'cores': {'in_use': 1, 'limit': 20, 'reserved': 0},
                'ecus': {'in_use': 5, 'limit': 20, 'reserved': 0},
                'local_gb': {'in_use': 20, 'limit': 1000, 'reserved': 0},
                'ram': {'in_use': 4136, 'limit': 51200, 'reserved': 0}
            }
        }
        filter_result = [
            {'cores': {'in_use': 11, 'limit': 20, 'reserved': 0},
             'ecus': {'in_use': 5, 'limit': 20, 'reserved': 0},
             'local_gb': {'in_use': 20, 'limit': 1000, 'reserved': 0},
             'ram': {'in_use': 4136, 'limit': 51200, 'reserved': 0},
             'tenant_id': '',
             'tenant_name': 'Project_admin',
             'volumes': {'in_use': 0, 'limit': 10, 'reserved': 0}
             }
        ]
        keypairs = []
        tenant = {'id': '5dd12337fcaf45a99269053caa8549f2', 'enabled': True,
                  'description': None, 'name': 'Project_admin'}
        user_info = {'id': '5dd12337fcaf45a99269053caa8549f2', 'enabled': True,
                     'description': None, 'name': 'Project_admin',
                     'tenantName': 'test1',
                     'email': 'hzrandd@corp.netease.com'}
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'
        headers = ''

        def fake_nova_request(self, req):
            return result, headers

        def fake_get_keypairs(tenant_id, auth_token):
            return keypairs

        def fake_get_user(userid, auth_token):
            return user_info

        def fake_get_tenant(tenantid, auth_token):
            return tenant

        def fake_filter_quotas(req, tenant_id, converted_result):
            return filter_result

        self.stubs.Set(server.Controller, '_nova_request', fake_nova_request)
        self.stubs.Set(ops_api, 'get_keypairs', fake_get_keypairs)
        self.stubs.Set(ops_api, 'get_user', fake_get_user)
        self.stubs.Set(ops_api, 'get_tenant', fake_get_tenant)
        self.stubs.Set(list_filter, 'filter_quotas', fake_filter_quotas)

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}
        mock.GET = ''

        controll = server.Controller()
        re = controll.list_all_quotas(mock, tenant_id)
        self.assertEqual(re, expect)

    def test_list_quotas(self):
        expect = {
            'quota_set':
            {
                'cores': 20,
                'ecus': 50,
                'ram': 50.0
            }
        }
        result = {
            'quota_set':
            {
                'cores': 20,
                'ecus': 50,
                'ram': 51200
            }
        }
        headers = ''
        target_id = '9b2ca68e-0628-487b-9e01-0dfd53e006ac'
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'

        def fake_nova_request(self, req):
            return result, headers

        self.stubs.Set(server.Controller, '_nova_request', fake_nova_request)
        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}
        mock.GET = ''

        controll = server.Controller()
        re = controll.list_quotas(mock, tenant_id, target_id)
        self.assertEqual(re, expect)
