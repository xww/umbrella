#
# Created on Dec 25, 2012
#
# @author: hzzhoushaoyu
#

import uuid
from webob.request import Request

from umbrella.api.list_operation import filter as list_filter
from umbrella.common import utils
import umbrella.openstack.api
from umbrella import tests


class FilterTest(tests.BaseTest):

    def test_get_value_by_key(self):
        item = {
                'name': 'test',
                'list': [
                         {
                          'name': 'listA'
                          },
                         {
                          'name': 'listB',
                          'type': 'private'
                          }
                         ]
                }
        # Test single layer
        key = 'name'
        value = utils.get_value_by_key(item, key)
        self.assertEqual(value, 'test')

        # Test multiple layer have multiple same key
        key = 'list/#list/name'
        value = utils.get_value_by_key(item, key)
        self.assertEqual(value, ['listA', 'listB'])

        # Test multiple layer have different key
        key = 'list/#list/type'
        value = utils.get_value_by_key(item, key)
        self.assertEqual(value, ['private'])

    def test_get_value_by_key_not_found(self):
        item = {
                'name': 'test',
                'list': [
                         {
                          'name': 'listA'
                          },
                         {
                          'name': 'listB',
                          'type': 'private'
                          }
                         ]
                }
        key = 'not-exists'
        value = utils.get_value_by_key(item, key)
        self.assertEqual(value, None)

        key = 'list/#list/not-exists'
        value = utils.get_value_by_key(item, key)
        self.assertEqual(value, None)

    def test_and_(self):
        items = [{
                'name': 'testA',
                'list': [
                         {
                          'name': 'listAA'
                          },
                         {
                          'name': 'listAB',
                          'type': 'private'
                          }
                         ],
                  'is_public': True
                },
                 {
                'name': 'testB',
                'list': [
                         {
                          'name': 'listBA'
                          },
                         {
                          'name': 'listBB',
                          'type': 'private'
                          }
                         ],
                  'is_public': False
                }]
        # test no search
        keys = []
        values = {}
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, items)

        # test single key
        keys = ['name']
        values = dict(name='testA')
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [items[0]])

        keys = ['list/#list/name']
        values = dict({'list/#list/name': 'listAA'})
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [items[0]])

        keys = ['is_public']
        values = dict(is_public='1')
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [items[0]])

        keys = ['is_public']
        values = dict(is_public='0')
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [items[1]])

        # test multiple key
        keys = ['name', 'list/#list/name']
        values = dict(name='testB')
        values.update({'list/#list/name': 'listB'})
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [])

        # test not found
        keys = ['name']
        values = dict(name='not-exists')
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [])

        keys = ['list/#list/name']
        values = dict({'list/#list/name': 'not-exits'})
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [])

        # test one key not match
        keys = ['name', 'list/#list/name']
        values = dict(name='not-exits')
        values.update({'list/#list/name': 'listB'})
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [])

        keys = ['name', 'list/#list/name']
        values = dict(name='t')
        values.update({'list/#list/name': 'not-exits'})
        result = list_filter.and_(items, keys, values)
        self.assertEqual(result, [])

    def test_or_(self):
        items = [{
                'name': 'testA',
                'tenant_id': '000-001',
                'list': [
                         {
                          'name': 'listA'
                          },
                         {
                          'name': 'listA',
                          'type': 'private'
                          }
                         ],
                  'is_public': True
                },
                 {
                'name': 'testB',
                'tenant_id': '000-002',
                'list': [
                         {
                          'name': 'listB'
                          },
                         {
                          'name': 'listB',
                          'type': 'private'
                          }
                         ],
                  'is_public': False
                }]
        tenant_key = 'tenant_id'
        # test no search
        keys = []
        value = None
        result = list_filter.or_(items, keys, value, tenant_key, None)
        self.assertEqual(result, items)

        # test single key
        keys = ['name']
        value = 'testA'
        result = list_filter.or_(items, keys, value, tenant_key, None)
        self.assertEqual(result, [items[0]])

        keys = ['list/#list/name']
        value = 'listB'
        result = list_filter.or_(items, keys, value, tenant_key, None)
        self.assertEqual(result, [items[1]])

        keys = ['is_public']
        value = '1'
        result = list_filter.or_(items, keys, value, tenant_key, None)
        self.assertEqual(result, [items[0]])

        keys = ['is_public']
        value = '0'
        result = list_filter.or_(items, keys, value, tenant_key, None)
        self.assertEqual(result, [items[1]])

        # test keys and tenant id
        # tenant id and value matched
        keys = ['name', 'list/#list/name']
        value = 'testB'
        result = list_filter.or_(items, keys, value, tenant_key, '000-002')
        self.assertEqual(result, [items[1]])

        # tenant id matched
        keys = ['name', 'list/#list/name']
        value = 'not-exists'
        result = list_filter.or_(items, keys, value, tenant_key, '000-002')
        self.assertEqual(result, [items[1]])

        # value matched
        keys = ['name', 'list/#list/name']
        value = 'test'
        result = list_filter.or_(items, keys, value, tenant_key, 'not-exits')
        # Note(hzrandd): have not name=test item.
        self.assertEqual(result, [])

        # all not matched
        keys = ['name', 'list/#list/name']
        value = 'not-exists'
        result = list_filter.or_(items, keys, value, tenant_key, 'not-exits')
        self.assertEqual(result, [])

    def test_filter_servers(self):
        def make_server_fixture(**kwargs):
            server = {
                    "OS-DCF:diskConfig": "MANUAL",
                    "OS-EXT-SRV-ATTR:host": "10-120-32-144",
                    "OS-EXT-SRV-ATTR:hypervisor_hostname": "10-120-32-144",
                    "OS-EXT-SRV-ATTR:instance_name": "instance-00000004",
                    "OS-EXT-STS:power_state": "shutdown",
                    "OS-EXT-STS:task_state": None,
                    "OS-EXT-STS:vm_state": "stopped",
                    "availability_zone": "nova",
                    "private_floating_ips": [
                                        {
                                            "addr": "10.120.31.1",
                                            "version": 4
                                        }],
                    "public_floating_ips": [
                                        {
                                            "addr": "10.120.240.225",
                                             "version": 4
                                        }],
                    "fixed_ips": [
                                        {
                                            "addr": "10.0.0.2",
                                            "is_floating_ip": False,
                                            "type": "fixed",
                                            "version": 4
                                        }],
                    "network_qos_public": {"rate": 111},
                    "network_qos_private": {"rate": 111},
                    "created": "2012-12-05 06:40:02",
                    "flavor-OS-FLV-DISABLED:disabled": False,
                    "flavor-OS-FLV-EXT-DATA:ephemeral": 0,
                    "flavor-disk": 10,
                    "flavor-id": "6",
                    "flavor-name": "debug",
                    "flavor-os-flavor-access:is_public": True,
                    "flavor-ram": 1,
                    "flavor-rxtx_factor": 1.0,
                    "flavor-swap": "",
                    "flavor-vcpus": 1,
                    "hostId":
                "f70cb0956039137219ceb9ff446a2c2ff7cf0a3692d789c7486c9d9a",
                    "id": "71c5ab41-b8e7-4d40-8439-7c955bd27a94",
                    "image-checksum": "c51dcf61b1a1058f221fc754bee48caf",
                    "image-container_format": "ovf",
                    "image-created_at": "2012-11-03T03:09:48",
                    "image-deleted": "False",
                    "image-disk_format": "raw",
                    "image-id": "75c8bf1d-4c2a-4835-acde-94992c5e50e1",
                    "image-is_public": "True",
                    "image-min_disk": "0",
                    "image-min_ram": "0",
                    "image-name": "precise-test",
                    "image-owner": "dc32392af0ae4a098fb7235760077fa6",
                    "image-owner-name": "admin",
                    "image-protected": "False",
                    "image-size": "211419136",
                    "image-status": "active",
                    "image-updated_at": "2012-11-05T02:12:04",
                    "key_name": None,
                    "metadata": {},
                    "name": "test-1",
                    "running_seconds": 273438.759003,
                    "security_groups": [
                        {
                            "name": "default"
                        }
                    ],
                    "status": "SHUTOFF",
                    "tenant_id": u"dc32392af0ae4a098fb7235760077fa6",
                    "tenant_name": "admin",
                    "updated": "2012-12-05T11:36:12Z",
                    "user_id": u"f2665c1140c54a03a98110cb86262ec3"
                }
            server.update(**kwargs)
            return server
        UUID1 = str(uuid.uuid4())
        UUID2 = str(uuid.uuid4())
        UUID3 = str(uuid.uuid4())
        UUID4 = str(uuid.uuid4())
        servers = [
                   make_server_fixture(**{"name": "test1",
                                        "OS-EXT-SRV-ATTR:host": "host1",
                                        "fixed_ips": [{"addr": "10.0.0.1"}],
                                        "status": "active",
                                        "tenant_id": UUID1,
                                        "tenant_name": "Project_nvs"}),
                   make_server_fixture(**{"name": "test2",
                                        "OS-EXT-SRV-ATTR:host": "host2",
                                        "fixed_ips": [{"addr": "10.0.0.2"}],
                                        "status": "active",
                                        "tenant_id": UUID2,
                                        "tenant_name": "Project_admin"}),
                   make_server_fixture(**{"name": "test3",
                                        "OS-EXT-SRV-ATTR:host": "host3",
                                        "fixed_ips": [{"addr": "10.0.0.12"}],
                                        "status": "active",
                                        "tenant_id": UUID3,
                                        "tenant_name": "admin"}),
                   make_server_fixture(**{"name": "test4",
                                        "OS-EXT-SRV-ATTR:host": "host4",
                                        "fixed_ips": [{"addr": "10.0.0.4"}],
                                        "status": "error",
                                        "tenant_id": UUID4,
                                        "tenant_name": "Project_test"})
                   ]
        # And condition
        req = Request.blank(path="/servers?relationship=and"
                            "&tenantid=%s" % UUID1)
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[0]])

        req = Request.blank(path="/servers?relationship=and"
                            "&tenant_name=test")
        result = list_filter.filter_servers(req, servers)
        # Note(hzrandd): have not tenant_name=test itme.
        self.assertEquals(result, [])

        req = Request.blank(path="/servers?relationship=and"
                            "&name=test3")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[2]])

        req = Request.blank(path="/servers?relationship=and"
                            "&host=host2")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[1]])

        req = Request.blank(path="/servers?relationship=and"
                            "&fixed_ip=0.12")
        result = list_filter.filter_servers(req, servers)
        # Note(hzrandd): have not fixed_ip=0.12 itme.
        self.assertEquals(result, [])

        req = Request.blank(path="/servers?relationship=and"
                            "&status=error")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[3]])

        # Multiple and condition
        req = Request.blank(path="/servers?relationship=and"
                            "&host=host1&status=active")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[0]])

        req = Request.blank(path="/servers?relationship=and"
                            "&host=host1&status=error")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [])

        # Or condition
        req = Request.blank(path="/servers?relationship=or"
                            "&key=error")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[3]])

        req = Request.blank(path="/servers?relationship=or"
                            "&key=host2")
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[1]])

        # Multiple or condition
        req = Request.blank(path="/servers?relationship=or"
                            "&tenantid=%s&key=host2" % UUID1)
        result = list_filter.filter_servers(req, servers)
        self.assertEquals(result, [servers[0], servers[1]])

    def test_filter_images(self):
        images = [
                    {
                        "checksum": "1493354e149683f532a76aaeefba05a3",
                        "container_format": "ovf",
                        "created_at": "2012-11-19T05:55:01",
                        "deleted": False,
                        "deleted_at": None,
                        "disk_format": "raw",
                        "id": "2d49687f-257f-4228-a788-8113ac829914",
                        "is_public": True,
                        "min_disk": 0,
                        "min_ram": 0,
                        "name": "test-resize",
                        "owner": "dc32392af0ae4a098fb7235760077fa6",
                        "owner_name": "admin",
                        "properties": {
                                      "image_location": "snapshot",
                                      "image_state": "available",
                                      "image_type": "snapshot",
                                      "description": "description test",
                                      "instance_uuid":
                                        "c3fc303a-1f18-4f8d-862a-c13b22be15e9"
                                     },
                        "protected": False,
                        "size": 195821568,
                        "status": "active",
                        "updated_at": "2012-11-19T05:55:38"
                    },
                    {
                        "checksum": "abcd",
                        "container_format": "ovf",
                        "created_at": "2013-01-19T05:55:01",
                        "deleted": False,
                        "deleted_at": None,
                        "disk_format": "raw",
                        "id": "abcd",
                        "is_public": False,
                        "min_disk": 0,
                        "min_ram": 0,
                        "name": "debian",
                        "owner": "abcd",
                        "owner_name": "Project_abcd",
                        "properties": {
                                      "image_location": "snapshot",
                                      "image_state": "available",
                                      "image_type": "snapshot",
                                      "description": u"abcd",
                                      "instance_uuid":
                                        "c3fc303a-1f18-4f8d-862a-c13b22be15e9"
                                     },
                        "protected": False,
                        "size": 195821568,
                        "status": "killed",
                        "updated_at": "2012-11-19T05:55:38"
                    },
                ]
        req = Request.blank(path="/images?relationship=and"
                            "&name=debian")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                        "&id=2d49687f-257f-4228-a788-8113ac829914")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[0]])

        req = Request.blank(path="/images?relationship=and"
                            "&desc=abcd")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&is_public=1")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[0]])

        req = Request.blank(path="/images?relationship=and"
                            "&is_public=0")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&status=killed")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&tenantid=abcd")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&tenantname=admain")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[0], images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&tenantid=abcd&status=killed")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

        req = Request.blank(path="/images?relationship=and"
                            "&tenantid=abcd&status=active")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [])

        req = Request.blank(path="/images?relationship=or"
                            "&tenantid=abcd&key=active")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, images)

        req = Request.blank(path="/images?relationship=or"
                            "&key=killed")
        result = list_filter.filter_images(req, images)
        self.assertEquals(result, [images[1]])

    def test_filter_security_groups(self):
        security_groups = [
                        {
                            "description": "default",
                            "id": 3,
                            "name": "default",
                            "tenant_id": "76339e4d5a0d449a90805963b1757c15",
                            "tenant_name": "Project_test"
                        },
                        {
                            "description": "test-demo",
                            "id": 4,
                            "name": "test-demo",
                            "tenant_id": "76339e4d5a0d449a90805963b1757c15",
                            "tenant_name": "Project_test"
                        },
                        {
                            "description": "default",
                            "id": 1,
                            "name": "default",
                            "tenant_id": "dc32392af0ae4a098fb7235760077fa6",
                            "tenant_name": "admin"
                        },
                        {
                            "description": "test-admin",
                            "id": 2,
                            "name": "test-admin",
                            "tenant_id": "dc32392af0ae4a098fb7235760077fa6",
                            "tenant_name": "admin"
                        }
                        ]
        # And condition
        req = Request.blank(path="/security_groups?relationship=and"
                                 "&name=test-demo"
                                 "&desc=test-demo")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[1]])

        req = Request.blank(path="/security_groups?relationship=and"
                                 "&tenant_name=Project_test")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[0], security_groups[1]])

        req = Request.blank(path="/security_groups?relationship=and"
                                 "&desc=test-demo")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[1]])

        req = Request.blank(path="/security_groups?relationship=and"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[2], security_groups[3]])

        # Multiple and Condition
        req = Request.blank(path="/security_groups?relationship=and"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6"
                        "&name=default")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[2]])

        req = Request.blank(path="/security_groups?relationship=and"
                         "&desc=test-admin&name=test-admin")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[3]])

        # Or condition
        req = Request.blank(path="/security_groups?relationship=or"
                                 "&key=admin")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[2], security_groups[3]])

        req = Request.blank(path="/security_groups?relationship=or"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[2], security_groups[3]])

        # Multiple or condition
        req = Request.blank(path="/security_groups?relationship=or"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6"
                        "&key=default")
        result = list_filter.filter_security_groups(req, security_groups)
        self.assertEquals(result, [security_groups[0], security_groups[2],
                                   security_groups[3]])

    def test_filter_floating_ips(self):
        ips = [{
                "instance_name": "test",
                "ip": "10.120.240.26",
                "fixed_ip": "10.0.0.12",
                "instance_id":"68",
                "project_id": "dc32392af0ae4a098fb7235760077fa6",
                "project_name": "admin",
                "type": "private",
                "id": 1,
                "pool": "lan"
                },
               {
                "instance_name": "test",
                "ip": "10.120.240.26",
                "fixed_ip": "10.0.0.12",
                "instance_id":"68",
                "project_id": "dc32392af0ae4a098fb7235760077fa6",
                "project_name": "admin",
                "type": "private",
                "id": 1,
                "pool": "lan"
                },
#            &ip=10.120.240.6&umbrella_tenantid="                   |~
#"              "dc32392af0ae4a098fb7235760077fa6""
               {
                "instance_name": "fl",
                "ip": "10.120.240.6",
                "fixed_ip": "10.0.0.13",
                "instance_id":"82",
                "project_id": "abcd",
                "project_name": "Project_abcd",
                "type": "private",
                "id": 1,
                "pool": "lan"
                }]
        # And condition
        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&ip=10.120.240.26")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [ips[0], ips[1]])

        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&type=private")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, ips)

        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&pool=lan")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, ips)

        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&tenant_name=admin")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [ips[0], ips[1]])

        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&instance_name=fl")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [ips[2]])

        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&tenantid=8")
        result = list_filter.filter_floating_ips(req, ips)
        # Note(hzrandd): precise match tenantid=8,have not this item.
        self.assertEquals(result, [])

        # Multiple and condition
        req = Request.blank(path="/floating_ips?relationship=and"
                                 "&ip=10.120.240.6&tenantid="
                                 "dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [])

        # Or condition
        req = Request.blank(path="/floating_ips?relationship=or"
                                 "&tenantid=fl")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [])

        req = Request.blank(path="/floating_ips?relationship=or"
                                 "&key=test")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [ips[0], ips[1]])

        req = Request.blank(path="/floating_ips?relationship=or"
                                 "&key=test&tenantid=fl")
        result = list_filter.filter_floating_ips(req, ips)
        self.assertEquals(result, [ips[0], ips[1]])

    def test_filter_keypairs(self):
        keypairs = [
                    {
                        "fingerprint": "bf:ae:ac:34:44:c9:a8:0e:"
                                       "f5:04:67:35:a5:28:4d:7c",
                        "name": "test-demo",
                        "public_key": "ssh-rsa AAAxx== Generated by Nova",
                        "user_id": "e0ef2619442f472c86951f84b210062d",
                        "user_name": "demo"
                    },
                    {
                        "fingerprint": "2c:71:d7:58:dc:cc:9c:5a:"
                                       "10:9b:b6:f3:dc:79:26:66",
                        "name": "test-admin",
                        "public_key": "ssh-rsa AAAxxbgx== Generated by Nova",
                        "user_id": "ad35ccc469824255a20174f99cb12ee0",
                        "user_name": "admin"
                    }
                    ]
        # And condition
        req = Request.blank(path="/keypairs?relationship=and"
                                 "&userid="
                                 "ad35ccc469824255a20174f99cb12ee0")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[1]])

        req = Request.blank(path="/keypairs?relationship=and"
                                 "&name=test-demo")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[0]])

        req = Request.blank(path="/keypairs?relationship=and"
                                "&fingerprint=bf:ae:ac:34:44:"
                                "c9:a8:0e:f5:04:67:35:a5:28:4d:7c")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[0]])

        req = Request.blank(path="/keypairs?relationship=and"
                                 "&user_name=demo")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[0]])

        # Multiple and condition
        req = Request.blank(path="/keypairs?relationship=and"
                                 "&name=test-admin&userid="
                                 "ad35ccc469824255a20174f99cb12ee0")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[1]])

        # Or condition
        req = Request.blank(path="/keypairs?relationship=or"
                                 "&key=test-demo")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, [keypairs[0]])

        req = Request.blank(path="/keypairs?relationship=or"
                                 "&key=test-demo&userid="
                                 "ad35ccc469824255a20174f99cb12ee0")
        result = list_filter.filter_keypairs(req, keypairs)
        self.assertEquals(result, keypairs)

    def test_filter_instance_error(self):
        errors = [
                    {
                        "code": "500",
                        "created": "2012-12-05T06:25:33Z",
                        "message": "NoValidHost",
                        "name": "test",
                        "tenant_id": "dc32392af0ae4a098fb7235760077fa6",
                        "uuid": "c06f051f-1af6-48ff-90fd-871556771e99"
                    },
                   {
                        "code": "404",
                        "created": "2012-12-05T07:29:35Z",
                        "message": "BadRequest",
                        "name": "abcd",
                        "tenant_id": "ad35ccc469824255a20174f99cb12ee0",
                        "uuid": "33b960f8-1e42-4c55-b83b-96ac0b3c8b8e"
                    }
                ]
        req = Request.blank("/instance/error?relationship=and"
                            "&name=abcd")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/instance/error?relationship=and"
                        "&uuid=c06f051f-1af6-48ff-90fd-871556771e99")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/instance/error?relationship=and"
                            "&code=404")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/instance/error?relationship=and"
                            "&created=2012-12-05T07:29:35Z")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/instance/error?relationship=and"
                            "&message=BadRequest")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/instance/error?relationship=and"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[0]])

        # Multiple and condition
        req = Request.blank("/instance/error?relationship=and"
                            "&tenantid=dc32392&umbrella_message=BadR")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [])

        req = Request.blank("/instance/error?relationship=and"
                          "&tenantid=ad35ccc469824255a20174f99cb12ee0"
                          "&message=BadRequest")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[1]])

        # Or condition
        req = Request.blank("/instance/error?relationship=or"
                            "&tenantid=dc32392af")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/instance/error?relationship=or"
                            "&key=NoValid")
        result = list_filter.filter_instance_error(req, errors)
        # Note(hzrandd): have not key=NoValid item.
        self.assertEqual(result, [])

        # Multiple or condition
        req = Request.blank("/instance/error?relationship=or"
                          "&tenantid=dc32392af0ae4a098fb7235760077fa6"
                          "&message=BadRe")
        result = list_filter.filter_instance_error(req, errors)
        self.assertEqual(result, [errors[0]])

    def test_filter_snapshot_error(self):
        errors = [
                    {
                        "created": "2012-12-05T06:43:19",
                        "desc": "create snapshot failed.",
                        "id": "33b960f8-1e42-4c55-b83b-96ac0b3c8b8e",
                        "name": "test",
                        "owner": "abcd"
                    },
                    {
                        "created": "2013-02-04 22:18:08",
                        "desc": "Instance 5c845d55-d0a8-4268-9a43-9f61d1da435c"
                                "create snapshot failed.",
                        "id": "04e39603-3686-4dae-9a5f-cc1088a41d79",
                        "name": "snapShot1359987434439",
                        "owner": "dc32392af0ae4a098fb7235760077fa6"
                    }
                ]
        req = Request.blank("/snapshot/error?relationship=and"
                           "&id=33b960f8-1e42-4c55-b83b-96ac0b3c8b8e")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/snapshot/error?relationship=and"
                            "&created=2013-02-04 22:18:08")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/snapshot/error?relationship=and"
                         "&desc=5c845d55")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [])

        req = Request.blank("/snapshot/error?relationship=and"
                            "&name=test")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/snapshot/error?relationship=and"
                            "&tenantid=abcd")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/snapshot/error?relationship=and"
                            "&tenantid=abcd"
                           "&id=33b960f8-1e42-4c55-b83b-96ac0b3c8b8e")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[0]])

        req = Request.blank("/snapshot/error?relationship=and"
                            "&tenantid=abcd&id=04e39603-")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [])

        req = Request.blank("/snapshot/error?relationship=or"
                            "&key=abcd")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [])

        req = Request.blank("/snapshot/error?relationship=or"
                           "&key=04e39603-3686-4dae-9a5f-cc1088a41d79"
                           "&tenantid=abcd")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, errors)

        req = Request.blank("/snapshot/error?relationship=or"
                         "&key=04e39603-3686-4dae-9a5f-cc1088a41d79")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[1]])

        req = Request.blank("/snapshot/error?relationship=or"
                            "&tenantid=abcd")
        result = list_filter.filter_snapshot_error(req, errors)
        self.assertEqual(result, [errors[0]])

    def test_filter_tenants_usages(self):
        usages = [
                    {
                        "public_qos_used": 50,
                        "private_qos_used": 100,
                        "tenant_id": "dc32392af0ae4a098fb7235760077fa6"
                    }
                ]
        req = Request.blank("/snapshot/error?relationship=and"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_tenants_usages(req, usages)
        self.assertEqual(result, usages)

        req = Request.blank("/snapshot/error?relationship=and"
                            "&tenantid=not-exists")
        result = list_filter.filter_tenants_usages(req, usages)
        self.assertEqual(result, [])

        req = Request.blank("/snapshot/error?relationship=or"
                        "&tenantid=dc32392af0ae4a098fb7235760077fa6")
        result = list_filter.filter_tenants_usages(req, usages)
        self.assertEqual(result, usages)

        req = Request.blank("/snapshot/error?relationship=or"
                            "&tenantid=not-exists")
        result = list_filter.filter_tenants_usages(req, usages)
        self.assertEqual(result, [])

    def test_filter_host_usages(self):
        usages = [
                    {
                        "hostname": "host1",
                        "availability_zone": "nova",
                        "ecus_used": 10,
                        "local_gb_used": 40,
                        "memory_mb_used": 10240,
                        "public_ips_used": 1,
                        "private_ips_used": 10,
                        "public_qos_used": 20,
                        "private_qos_used": 123,
                        "servers_used": 5,
                        "vcpus_used": 5
                    },
                    {
                        u"hostname": "host2",
                        "availability_zone": "nova1",
                        "ecus_used": 20,
                        "local_gb_used": 100,
                        "memory_mb_used": 20480,
                        "public_ips_used": 2,
                        "private_ips_used": 10,
                        "public_qos_used": 30,
                        "private_qos_used": 200,
                        "servers_used": 10,
                        "vcpus_used": 10
                    }
                ]
        req = Request.blank("/usages/host?relationship=and"
                            "&hostname=host1")
        result = list_filter.filter_host_usages(req, usages)
        self.assertEqual(result, [usages[0]])

        req = Request.blank("/usages/host?relationship=and"
                            "&az=nova1")
        result = list_filter.filter_host_usages(req, usages)
        self.assertEqual(result, [usages[1]])

        req = Request.blank("/usages/host?relationship=and"
                            "&hostname=host1"
                            "&az=nova1")
        result = list_filter.filter_host_usages(req, usages)
        self.assertEqual(result, [])

        req = Request.blank("/usages/host?relationship=or"
                            "&key=host2")
        result = list_filter.filter_host_usages(req, usages)
        self.assertEqual(result, [usages[1]])

        req = Request.blank("/usages/host?relationship=or"
                            "&key=host")
        result = list_filter.filter_host_usages(req, usages)
        # Note(hzrandd): have not key=host item.
        self.assertEqual(result, [])

    def test_filter_quotas(self):
        def make_quota_fixture(**kwargs):
            quota = {u'ecus': {
                        u'limit': 50,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'gigabytes': {
                        u'limit': 1000,
                        u'reserved': 0,
                        u'in_use': 0
                    },
                    u'private_floating_ips': {
                        u'limit': 10,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'ram': {
                        u'limit': 51200,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'floating_ips': {
                        u'limit': 10,
                        u'reserved': 0,
                        u'in_use': 2
                    },
                    u'instances': {
                        u'limit': 10,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'key_pairs': {
                        u'limit': 100,
                        u'reserved': 0,
                        u'in_use': 0
                    },
                    'tenant_id': u'dc32392af0ae4a098fb7235760077fa6',
                    u'cores': {
                        u'limit': 20,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'security_groups': {
                        u'limit': 10,
                        u'reserved': 0,
                        u'in_use': 0
                    }}
            for key in kwargs:
                if key == 'tenant_id':
                    quota.update(tenant_id=kwargs[key])
                    continue
                elif '/' not in key:
                    quota.update({key: kwargs[key]})
                    continue
                quota[key.split('/')[0]].update({
                                                 key.split('/')[1]: kwargs[key]
                                                 })
            return quota

        def fake_get_detault_quotas(tenant_id, target_id, auth_token):
            return dict(quota_set=make_quota_fixture(tenant_id=target_id,
                                                     ecus=50,
                                                     gigabytes=1000,
                                                     private_floating_ips=10,
                                                     ram=51200,
                                                     floating_ips=10,
                                                     instances=10,
                                                     key_pairs=100,
                                                     cores=20,
                                                     security_groups=10))

        self.stubs.Set(umbrella.openstack.api, "get_detault_quotas",
                       fake_get_detault_quotas)

        quotas = [make_quota_fixture(tenant_id="abcd",
                                     tenant_name="Project_abcd"),
                  make_quota_fixture(**{"security_groups/in_use": 5,
                                        "tenant_name": "admin"})]

        req = Request.blank("/quotas?relationship=and"
                            "&tenantid=e4a098fb")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[1]])

        req = Request.blank("/quotas?relationship=and"
                            "&tenantname=abcd")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[0]])

        req = Request.blank("/quotas?relationship=and"
                            "&security_groups_use=5")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[1]])

        req = Request.blank("/quotas?relationship=and"
                            "&instances_limit=10")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, quotas)

        req = Request.blank("/quotas?relationship=and"
                            "&tenantid=abcd"
                            "&security_groups_use=5")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [])

        req = Request.blank("/quotas?relationship=and"
                            "&tenantid=e4a098fb"
                            "&security_groups_use=5"
                            "&instances_limit=10")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[1]])

        req = Request.blank("/quotas?relationship=or"
                            "&tenantid=abc")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[0]])

        req = Request.blank("/quotas?relationship=or"
                            "&key=5")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, [quotas[1]])

        req = Request.blank("/quotas?relationship=or"
                            "&tenantid=abc"
                            "&key=5")
        result = list_filter.filter_quotas(req, None, quotas)
        self.assertEqual(result, quotas)

        # test default quota
        expect_default = {u'ecus': {
                                             'reserved': 0,
                                             'limit': 50,
                                             'in_use': 0
                                             },
                                   u'gigabytes': {
                                                  'reserved': 0,
                                                  'limit': 1000,
                                                  'in_use': 0
                                                  },
                                   u'private_floating_ips': {
                                                             'reserved': 0,
                                                             'limit': 10,
                                                             'in_use': 0},
                                   u'ram': {
                                            'reserved': 0,
                                            'limit': 51200,
                                            'in_use': 0},
                                   u'floating_ips': {
                                                     'reserved': 0,
                                                     'limit': 10,
                                                     'in_use': 0
                                                     },
                                   u'key_pairs': {
                                                  'reserved': 0,
                                                  'limit': 100,
                                                  'in_use': 0
                                                  },
                                   u'instances': {
                                                  'reserved': 0,
                                                  'limit': 10,
                                                  'in_use': 0
                                                  },
                                   'tenant_id': u'not-exists',
                                   u'cores': {
                                              'reserved': 0,
                                              'limit': 20,
                                              'in_use': 0
                                              },
                                   u'security_groups': {
                                                        'reserved': 0,
                                                        'limit': 10,
                                                        'in_use': 0
                                                        }
                                   }
        req = Request.blank("/quotas?relationship=and"
                            "&default=1"
                            "&tenantid=not-exists",
                            headers={"x-auth-token": "token"})
        result = list_filter.filter_quotas(req, "tenant-id", quotas)
        self.assertEqual(result, [expect_default])

        # Item exists but is abandoned by filter,
        # show the value ignoring filter.
        req = Request.blank("/quotas?relationship=and"
                            "&default=1"
                            "&tenantid=abcd"
                            "&security_groups_use=5",
                            headers={"x-auth-token": "token"})
        result = list_filter.filter_quotas(req, "tenant-id", quotas)
        self.assertEqual(result, [quotas[0]])

        # ignore default in or condition
        req = Request.blank("/quotas?relationship=or"
                            "&default=1"
                            "&tenantid=not-exists",
                            headers={"x-auth-token": "token"})
        result = list_filter.filter_quotas(req, "tenant-id", quotas)
        self.assertEqual(result, [])

        req = Request.blank("/quotas?relationship=or"
                            "&default=1"
                            "&tenantid=not-exists"
                            "&key=5",
                            headers={"x-auth-token": "token"})
        result = list_filter.filter_quotas(req, "tenant-id", quotas)
        self.assertEqual(result, [quotas[1]])
