#
#Created on 2013-07-02
#
# @author: hzrandd
#
import mox

from umbrella.tests import base
from umbrella.api import statistic
from umbrella.monitor import manager
from umbrella.openstack import api as ops_api
from umbrella import context


class ControllerTest(base.IsolatedUnitTest):

    def test_index(self):
        expect = {
            'private_qos': {'platform_capacity': 2000},
            'memory_gb': {'platform_capacity': 7.72,
                          'platform_remainder': 5.72, 'platform_used': 2}
        }
        us = [
            {'memory_mb':
             {'platform_capacity': 7905,
              'platform_remainder': 5857, 'platform_used': 2048},
             'private_qos': {'platform_capacity': 2000}
             }
        ]
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'

        def fake_request_usages(self, level, az_name=None):
            return us

        self.stubs.Set(manager.Manager, 'request_usages', fake_request_usages)

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': 'b0d0dffb8d824b4f8a91d81e10d46150'}
        kwargs = {'is_admin': True}
        con = context.RequestContext(**kwargs)
        mock.context = con
        mock.GET = ''
        m.ReplayAll()

        controll = statistic.Controller()
        re = controll.index(mock, tenant_id)
        self.assertEqual(re, expect)
        m.VerifyAll()

    def test_show_by_host(self):
        expect = {
            'hosts':
            [
                {'public_ips_used': 0, 'private_ips_used': 0,
                 'hostname': 'ubunt', 'memory_mb_used': 2,
                 'availability_zone': 'nova'}, {'private_ips_used': 0,
                 'availability_zone': None, 'hostname': 'ubuntu',
                 'memory_gb': 3.86, 'public_ips_used': 0}
            ]
        }
        usages = [
            {
                'memory_mb':
                {'ubuntu_used': 2,
                 'ubunt':
                 [
                     {'instance_id':
                      'ff6462be-d760-4f57-8870-16928e7056d2',
                      'memory_mb': 2.0, 'host': 'ubunt',
                      'project_id': '5dd12337fcaf45a99269053caa8549f2'}
                 ]
                 }
            }
        ]
        zones = {
            'availability_zones':
            [
                {'zoneState': 'available',
                 'hosts': ['ubunt'], 'zoneName': 'nova'}
            ]
        }
        hosts_capacity = {'ubuntu': {'memory_mb': 3955}}
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'
        items = {'ubunt': {'memory_mb_used': 2}}

        def fake_request_usages(self, level, az_name=None):
            return usages

        def fake_get_hosts_capacity(tenant_id, auth_token):
            return hosts_capacity

        def fake_get_hosts_az(tenant_id, auth_token):
            return zones

        def fake_construct_usage(self, usages):
            return items

        self.stubs.Set(manager.Manager, 'request_usages', fake_request_usages)
        self.stubs.Set(ops_api, 'get_hosts_capacity', fake_get_hosts_capacity)
        self.stubs.Set(ops_api, 'get_hosts_az', fake_get_hosts_az)
        self.stubs.Set(statistic.Controller,
                       '_construct_usage', fake_construct_usage)

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}
        kwargs = {'is_admin': True}
        con = context.RequestContext(**kwargs)
        mock.context = con
        mock.GET = ''
        m.ReplayAll()

        controll = statistic.Controller()
        re = controll.show_by_host(mock, tenant_id)
        self.assertEqual(re, expect)
        m.VerifyAll()

    def test_list_platform_usage(self):
        expect = [
            {'values':
             [
                 {'source': 0, 'currentValue': 1.86, 'statistics': 'maximum',
                  'description': 'remain_memory_gb',
                  'dimension': 'Platform=NVSPlatform',
                  'metricName': 'remain_memory_gb'},
                 {'source': 0, 'currentValue': 2.0, 'statistics': 'maximum',
                  'description': 'memory_gb',
                  'dimension': 'Platform=NVSPlatform',
                  'metricName': 'memory_gb'},
                 {'source': 0, 'currentValue': 3.86, 'statistics': 'maximum',
                  'description': 'total_memory_gb',
                  'dimension': 'Platform=NVSPlatform',
                  'metricName': 'total_memory_gb'}
             ],
             'name': 'memory_gb'
             }
        ]
        usages = [
            {
                'memory_mb':
                {'platform': [{u'host': u'ubuntu',
                               u'instance_id':
                               u'ff6462be-d760-4f57-8870-16928e7056d2',
                               u'memory_mb': 2048,
                               u'project_id':
                               u'5dd12337fcaf45a99269053caa8549f2'}],
                 'platform_capacity': 3955,
                 'platform_remainder': 1907,
                 'platform_used': 2048}}]
        tenant_id = '5dd12337fcaf45a99269053caa8549f2'

        def fake_request_usages(self, level, az_name=None):
            return usages

        self.stubs.Set(manager.Manager, 'request_usages', fake_request_usages)

        m = mox.Mox()
        mock = m.CreateMockAnything()
        mock.headers = {'x-auth-token': '66c9811f61d34906b8ae57ae6a47ee52'}
        mock.GET = ''
        kwargs = {'is_admin': True}
        con = context.RequestContext(**kwargs)
        mock.context = con

        m.ReplayAll()
        controll = statistic.Controller()
        re = controll.list_platform_usage(mock, tenant_id)
        self.assertEqual(re, expect)
        m.VerifyAll()
