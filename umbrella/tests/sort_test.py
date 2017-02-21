#
# Created on Jan 6, 2013
#
# @author: hzzhoushaoyu
#

import copy
import unittest
import webob

from umbrella.common import exception
from umbrella.api.list_operation import sort as list_sort


item1 = {
          'tenant_id': '000-001',
          'tenant_name': 'Project_001',
          'name': 'item1',
          'OS-EXT-SRV-ATTR:host': 'hostB',
          'fixed_ips': [
                       {
                        'addr': '10.0.0.2'
                        },
                       {
                        'addr': '10.0.1.2'
                        }
                       ]
          }
item2 = {
          'tenant_id': '000-002',
          'tenant_name': 'Project_abcd',
          'name': 'item3',
          'OS-EXT-SRV-ATTR:host': 'hostC',
          'fixed_ips': [
                       {
                        'addr': '10.0.0.3'
                        },
                       {
                        'addr': '10.0.1.3'
                        }
                       ]
          }
item3 = {
          'tenant_id': '000-003',
          'tenant_name': 'Project_003',
          'name': 'item2',
          'OS-EXT-SRV-ATTR:host': 'hostA',
          'fixed_ips': [
                       {
                        'addr': '10.0.0.2'
                        },
                       {
                        'addr': '10.0.1.4'
                        }
                       ]
          }
item4 = {
         'tenant_id': '000-004',
          'name': 'item4',
          'OS-EXT-SRV-ATTR:host': 'hostB',
          'fixed_ips': [
                       {
                        'addr': '10.0.0.21'
                        },
                       {
                        'addr': '10.0.1.4'
                        }
                       ]
         }
item5 = {
         'tenant_id': '000-005',
          'name': 'item5',
          'OS-EXT-SRV-ATTR:host': 'hostB',
          'fixed_ips': []
         }
item6 = {
         'tenant_id': '000-006',
          'name': 'item6',
          'OS-EXT-SRV-ATTR:host': 'hostB',
          'fixed_ips': [
                        {
                         'addr': ''
                         }
                        ]
         }
item7 = {
         'tenant_id': '000-007',
          'name': 'item7',
          'OS-EXT-SRV-ATTR:host': 'hostB',
          'fixed_ips': [
                        {
                         'addr': '10.'
                         }
                        ]
         }
items = [item1, item2, item3]


class SortTest(unittest.TestCase):

    def test_map_opts_and_sort(self):
        def _map_sort_key(sort_key):
            mapped_key = {
                          'tenantid': 'tenant_id',
                          'name': 'name',
                          'host': 'OS-EXT-SRV-ATTR:host',
                          'fixed_ip': 'fixed_ips/#list/addr',
                          }
            return mapped_key.get(sort_key, None)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid&umbrella_sort_dir=desc')
        result = list_sort.map_opts_and_sort(req, items, _map_sort_key)
        self.assertEqual(result, [item3, item2, item1])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.map_opts_and_sort(req, items, _map_sort_key)
        self.assertEqual(result, [item1, item3, item2])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=host&umbrella_sort_dir=desc')
        result = list_sort.map_opts_and_sort(req, items, _map_sort_key)
        self.assertEqual(result, [item2, item1, item3])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip&umbrella_sort_dir=desc')
        result = list_sort.map_opts_and_sort(req, items, _map_sort_key)
        self.assertEqual(result, [item2, item3, item1])

    def test_sort_not_mapped(self):
        def _map_sort_key(sort_key):
            mapped_key = {
                          'tenantid': 'tenant_id',
                          'name': 'name',
                          'host': 'OS-EXT-SRV-ATTR:host',
                          'fixed_ip': 'fixed_ips/#list/addr',
                          }
            return mapped_key.get(sort_key, None)
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=not_exists')
        result = list_sort.map_opts_and_sort(req, items, _map_sort_key)
        self.assertEqual(result, [item1, item2, item3])

    def test_sort_servers_by_name(self):
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_servers(req, items)
        self.assertEqual(result, [item1, item3, item2])

    def test_sort_servers_by_tenant_name(self):
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenant_name')
        result = list_sort.sort_servers(req, items)
        self.assertEqual(result, [item1, item3, item2])

    def test_sort_servers_IP(self):
        servers = copy.deepcopy(items)
        servers.append(item4)
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip')
        result = list_sort.sort_servers(req, servers)
        self.assertEqual(result, [item1, item3, item2, item4])

    def test_sort_servers_no_IP(self):
        servers = copy.deepcopy(items)
        servers.append(item5)
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip')
        result = list_sort.sort_servers(req, servers)
        self.assertEqual(result, [item5, item1, item3, item2])

    def test_sort_servers_blank_IP(self):
        servers = copy.deepcopy(items)
        servers.append(item6)
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip')
        result = list_sort.sort_servers(req, servers)
        self.assertEqual(result, [item6, item1, item3, item2])

    def test_sort_servers_invalid_IP(self):
        servers = copy.deepcopy(items)
        servers.append(item7)
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip')
        self.assertRaises(exception.InvalidIP, list_sort.sort_servers,
                          req, servers)

    def test_sort_servers_fixed_ips(self):
        def generate_servers(fixed_ip):
            server = {
                   "fixed_ips": [
                                {
                                 "addr": fixed_ip
                                 }
                                ]
                   }
            return server
        servers = []
        fixed_ips = [u"10.120.40.40",
                     u"10.120.41.40",
                     u"10.120.42.80",
                     u"10.120.42.78"]
        for fixed_ip in fixed_ips:
            servers.append(generate_servers(fixed_ip))
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fixed_ip&umbrella_sort_dir=desc')
        result = list_sort.sort_servers(req, servers)
        expected = [generate_servers(fixed_ips[2]),
                    generate_servers(fixed_ips[3]),
                    generate_servers(fixed_ips[1]),
                    generate_servers(fixed_ips[0])]
        self.assertEqual(result, expected)

    def test_sort_floating_ips(self):
        floating_ips = [{
                        "instance_name": "bd",
                        "ip": "10.120.240.225",
                        "instance_id":"82fbc5f8-e60f-440a-a9a6-a5ab32cd2f68",
                        "project_id": "dc32392af0ae4a098fb7235760077fa6",
                        "project_name": "admin",
                        "type": "public",
                        "id": 1,
                        "pool": "nova2"
                        },
                        {
                        "instance_name": "de",
                        "ip": "10.120.241.224",
                        "instance_id":"82fbc5f8-e60f-440a-a9a6-a5ab32cd2f68",
                        "project_id": "abcd",
                        "project_name": "Project_abcd",
                        "type": "public",
                        "id": 1,
                        "pool": "nova1"
                        },
                        {
                        "instance_name": "ab",
                        "ip": "10.120.240.222",
                        "instance_id":"82fbc5f8-e60f-440a-a9a6-a5ab32cd2f68",
                        "project_id": "dc32392af0ae4a098fb7235760077fa6",
                        "project_name": "admin",
                        "type": "private",
                        "id": 1,
                        "pool": "nova"
                        }]
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[1],
                                  floating_ips[0],
                                  floating_ips[2]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenant_name')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[0],
                                  floating_ips[2],
                                  floating_ips[1]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=ip')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[2],
                                  floating_ips[0],
                                  floating_ips[1]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=type')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[2],
                                  floating_ips[0],
                                  floating_ips[1]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=pool')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[2],
                                  floating_ips[1],
                                  floating_ips[0]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=instance_name')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[2],
                                  floating_ips[0],
                                  floating_ips[1]])

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=instance_name&umbrella_sort_dir=desc')
        result = list_sort.sort_floating_ips(req, floating_ips)
        self.assertEqual(result, [floating_ips[1],
                                  floating_ips[0],
                                  floating_ips[2]])

    def test_floating_ips_unicode(self):
        def generate_floating_ips(ip):
            ips = {
                   "ip": ip
                   }
            return ips
        servers = []
        fixed_ips = [u"10.120.40.40",
                     u"10.120.41.40",
                     u"10.120.42.80",
                     u"10.120.42.78"]
        for fixed_ip in fixed_ips:
            servers.append(generate_floating_ips(fixed_ip))
        req = webob.Request.blank(
                '/sort?umbrella_sort_key=ip&umbrella_sort_dir=desc')
        result = list_sort.sort_floating_ips(req, servers)
        expected = [generate_floating_ips(fixed_ips[2]),
                    generate_floating_ips(fixed_ips[3]),
                    generate_floating_ips(fixed_ips[1]),
                    generate_floating_ips(fixed_ips[0])]
        self.assertEqual(result, expected)

    def test_sort_images(self):
        def generate_images(**kwargs):
            image = {
                     "owner": "abcd",
                     "owner_name": "Project_abcd",
                     "name": "test",
                     "id": "uuid",
                     "description": "test",
                     "size": "0",
                     "status": "active"
                     }
            image.update(**kwargs)
            return image
        image1 = generate_images(owner="ownerA",
                                 owner_name="Project_ownerA",
                                 name="image1",
                                 id="728a-bcd",
                                 description="test",
                                 size="100",
                                 status="active")
        image2 = generate_images(owner="admin",
                                 owner_name="Project_admin",
                                 name="ubuntu",
                                 id="bcd-728a",
                                 description="test",
                                 size="200",
                                 status="queued")
        image3 = generate_images(owner="opt",
                                 owner_name="Project_opt",
                                 name="image2",
                                 id="70",
                                 description="my image",
                                 size="150",
                                 status="killed")
        images = [image1, image2, image3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_images(req, images)
        expected = [image2, image3, image1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenant_name')
        result = list_sort.sort_images(req, images)
        expected = [image2, image3, image1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_images(req, images)
        expected = [image1, image3, image2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=id')
        result = list_sort.sort_images(req, images)
        expected = [image3, image1, image2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=description')
        result = list_sort.sort_images(req, images)
        expected = [image1, image2, image3]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=status')
        result = list_sort.sort_images(req, images)
        expected = [image1, image3, image2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=status&umbrella_sort_dir=desc')
        result = list_sort.sort_images(req, images)
        expected = [image2, image3, image1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=size')
        result = list_sort.sort_images(req, images)
        expected = [image1, image3, image2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=size&umbrella_sort_dir=desc')
        result = list_sort.sort_images(req, images)
        expected = [image2, image3, image1]
        self.assertEqual(result, expected)

    def test_sort_security_groups(self):
        def generate_security_groups(**kwargs):
            security_groups = {
                     "tenant_id": "abcd",
                     "tenant_name": "Project_abcd",
                     "name": "test",
                     "description": "test"
                     }
            security_groups.update(**kwargs)
            return security_groups
        security_groups1 = generate_security_groups(tenant_id="ownerA",
                                                    tenant_name="Project_owA",
                                                    name="sg1",
                                                    description="test")
        security_groups2 = generate_security_groups(tenant_id="admin",
                                                    tenant_name="Project_admi",
                                                    name="ubuntu",
                                                    description="test")
        security_groups3 = generate_security_groups(tenant_id="opt",
                                                    tenant_name="Project_opt",
                                                    name="sg2",
                                                    description="my sg")
        groups = [security_groups1, security_groups2, security_groups3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_security_groups(req, groups)
        expected = [security_groups2, security_groups3, security_groups1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenant_name')
        result = list_sort.sort_security_groups(req, groups)
        expected = [security_groups2, security_groups3, security_groups1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_security_groups(req, groups)
        expected = [security_groups1, security_groups3, security_groups2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=description')
        result = list_sort.sort_security_groups(req, groups)
        expected = [security_groups3, security_groups1, security_groups2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=description&umbrella_sort_dir=desc')
        result = list_sort.sort_security_groups(req, groups)
        expected = [security_groups1, security_groups2, security_groups3]
        self.assertEqual(result, expected)

    def test_umbrella_sort_keypairs(self):
        def generate_keypairs(**kwargs):
            keypairs = {
                     "user_id": "abcd",
                     "user_name": "Project_abcd",
                     "name": "test",
                     "fingerprint": "ab:cd:ef"
                     }
            keypairs.update(**kwargs)
            return keypairs
        key_pairs1 = generate_keypairs(user_id="ownerA",
                                       user_name="Project_ownerA",
                                       name="sg1",
                                       fingerprint="ab:cd:b1:c0:15:fe:8e:2c:13"
                                                   ":13:55:5a:14:77:74:92")
        key_pairs2 = generate_keypairs(user_id="admin",
                                       user_name="Project_admin",
                                       name="ubuntu",
                                       fingerprint="2c:71:d7:58:dc:cc:9c:5a:10"
                                                   ":9b:b6:f3:dc:79:26:66")
        key_pairs3 = generate_keypairs(user_id="opt",
                                       user_name="Project_opt",
                                       name="sg2",
                                       fingerprint="52:9b:76:e8:d0:32:c6:37:0a"
                                                   ":85:97:0c:fc:4a:1e:02")
        key_pairs = [key_pairs1, key_pairs2, key_pairs3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_keypairs(req, key_pairs)
        expected = [key_pairs2, key_pairs3, key_pairs1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=user_name')
        result = list_sort.sort_keypairs(req, key_pairs)
        expected = [key_pairs2, key_pairs3, key_pairs1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_keypairs(req, key_pairs)
        expected = [key_pairs1, key_pairs3, key_pairs2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fingerprint')
        result = list_sort.sort_keypairs(req, key_pairs)
        expected = [key_pairs2, key_pairs3, key_pairs1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=fingerprint&umbrella_sort_dir=desc')
        result = list_sort.sort_keypairs(req, key_pairs)
        expected = [key_pairs1, key_pairs3, key_pairs2]
        self.assertEqual(result, expected)

    def test_sort_quotas(self):
        def generate_quotas(**kwargs):
            return {
                    u'ecus': {
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
                    'tenant_name': u'admin',
                    u'cores': {
                        u'limit': 20,
                        u'reserved': 0,
                        u'in_use': 1
                    },
                    u'security_groups': {
                        u'limit': 10,
                        u'reserved': 0,
                        u'in_use': 0
                    }
                }
        quotas1 = generate_quotas()
        quotas2 = generate_quotas(tenant_id='abcd',
                                  tenant_name='Project_test')
        quotas3 = generate_quotas(tenant_id='test',
                                  tenant_name='Project_abcd')

        quotas = [quotas1, quotas2, quotas3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_instance_error(req, quotas)
        expected = [quotas1, quotas3, quotas2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenant_name')
        result = list_sort.sort_instance_error(req, quotas)
        expected = [quotas3, quotas2, quotas1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid&umbrella_sort_dir=desc')
        result = list_sort.sort_instance_error(req, quotas)
        expected = [quotas2, quotas3, quotas1]
        self.assertEqual(result, expected)

    def test_sort_instance_error(self):
        def generate_instance_error(**kwargs):
            instance_error = {
                     "tenant_id": "abcd",
                     "name": "test",
                     "uuid": "d39ead1a-9d68-4e44-9cbd-d42b86030d34",
                     "code": 500,
                     "created": "2013-01-01 00:00:00",
                     "message": "NoValidHost"
                     }
            instance_error.update(**kwargs)
            return instance_error

        instance_error1 = generate_instance_error(tenant_id="ownerA",
                                                  name="sg1",
                                                  code=404,
                                                  message="Not Found.")
        instance_error2 = generate_instance_error(tenant_id="admin",
                                                  name="ubuntu",
                                                  uuid="40f7f068-8274-4167-"
                                                       "943c-1d19b1efc307",
                                                  code=500,
                                                  created="2013-02-03 "
                                                          "10:00:00")
        instance_error3 = generate_instance_error(tenant_id="opt",
                                                  name="sg2",
                                                  uuid="f8d4690c-71cc-4fe9-"
                                                       "a347-950effa1ad25",
                                                  created="2013-02-03 "
                                                          "09:00:00",
                                                  message="")
        instance_errors = [instance_error1, instance_error2, instance_error3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error2, instance_error3, instance_error1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error1, instance_error3, instance_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=uuid')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error2, instance_error1, instance_error3]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=code')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error1, instance_error2, instance_error3]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=created')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error1, instance_error3, instance_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=message')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error3, instance_error1, instance_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=message&umbrella_sort_dir=desc')
        result = list_sort.sort_instance_error(req, instance_errors)
        expected = [instance_error2, instance_error1, instance_error3]
        self.assertEqual(result, expected)

    def test_sort_snapshot_error(self):
        def generate_snapshot_error(**kwargs):
            instance_error = {
                     "owner": "abcd",
                     "name": "test",
                     "id": "d39ead1a-9d68-4e44-9cbd-d42b86030d34",
                     "created": "2013-01-01 00:00:00",
                     "desc": "NoValidHost"
                     }
            instance_error.update(**kwargs)
            return instance_error

        snapshot_error1 = generate_snapshot_error(owner="ownerA",
                                                  name="sg1",
                                                  desc="Not Found.")
        snapshot_error2 = generate_snapshot_error(owner="admin",
                                                  name="ubuntu",
                                                  id="40f7f068-8274-4167-"
                                                       "943c-1d19b1efc307",
                                                  created="2013-02-03 "
                                                          "10:00:00")
        snapshot_error3 = generate_snapshot_error(owner="opt",
                                                  name="sg2",
                                                  id="f8d4690c-71cc-4fe9-"
                                                       "a347-950effa1ad25",
                                                  created="2013-02-03 "
                                                          "09:00:00",
                                                  desc="")
        snapshot_errors = [snapshot_error1, snapshot_error2, snapshot_error3]

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=tenantid')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error2, snapshot_error3, snapshot_error1]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=name')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error1, snapshot_error3, snapshot_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=id')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error2, snapshot_error1, snapshot_error3]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=created')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error1, snapshot_error3, snapshot_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=desc')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error3, snapshot_error1, snapshot_error2]
        self.assertEqual(result, expected)

        req = webob.Request.blank(
                '/sort?umbrella_sort_key=desc&umbrella_sort_dir=desc')
        result = list_sort.sort_snapshot_error(req, snapshot_errors)
        expected = [snapshot_error2, snapshot_error1, snapshot_error3]
        self.assertEqual(result, expected)

    def test_sort_host_usages(self):
        host_usage1 = Utils.generate_usages(hostname="hostA",
                                            availability_zone="nova",
                                            public_qos_used=1)
        host_usage2 = Utils.generate_usages(hostname="hostB",
                                            availability_zone="nova2",
                                            servers_used=5,
                                            vcpus_used=5,
                                            public_qos_used=5)
        host_usage3 = Utils.generate_usages(hostname="hostC",
                                            availability_zone="nova1",
                                            servers_used=15,
                                            vcpus_used=15,
                                            public_ips_used=5,
                                            public_qos_used=10)
        usages = [host_usage1, host_usage2, host_usage3]

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "hostname")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                              [host_usage1, host_usage3, host_usage2],
                              "availability_zone")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        [host_usage2, host_usage1, host_usage3], "servers")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        [host_usage2, host_usage1, host_usage3], "vcpus")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "ecus")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "local_gb")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "memory_gb")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "private_ips")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "public_ips")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "private_qos")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        usages, "public_qos")

        Utils.usage_test_case(self, list_sort.sort_host_usage, usages,
                        [host_usage3, host_usage2, host_usage1],
                        "public_qos", "desc")

    def test_sort_tenants_usages(self):
        tenant_usage1 = Utils.generate_usages(tenant_id="ownerA",
                                        public_qos_used=1)
        tenant_usage2 = Utils.generate_usages(tenant_id="admin",
                                      servers_used=5,
                                      vcpus_used=5,
                                      public_qos_used=5)
        tenant_usage3 = Utils.generate_usages(tenant_id="opt",
                                      servers_used=15,
                                      vcpus_used=15,
                                      public_ips_used=5,
                                      public_qos_used=10)
        usages = [tenant_usage1, tenant_usage2, tenant_usage3]

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        [tenant_usage2, tenant_usage3, tenant_usage1],
                        "tenantid")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        [tenant_usage2, tenant_usage1, tenant_usage3],
                        "servers")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        [tenant_usage2, tenant_usage1, tenant_usage3], "vcpus")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "ecus")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "local_gb")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "memory_gb")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "private_ips")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "public_ips")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "private_qos")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        usages, "public_qos")

        Utils.usage_test_case(self, list_sort.sort_tenants_usage, usages,
                        [tenant_usage3, tenant_usage2, tenant_usage1],
                        "public_qos", "desc")


class Utils(object):

    @staticmethod
    def usage_test_case(testcase_obj, sort_method, sort_list, expected,
                        umbrella_sort_key, umbrella_sort_dir="asc"):
        req = webob.Request.blank('/sort?umbrella_sort_key=%s'
                                  '&umbrella_sort_dir=%s' %
                                  (umbrella_sort_key, umbrella_sort_dir))
        result = sort_method(req, sort_list)
        testcase_obj.assertEqual(expected, result)

    @staticmethod
    def generate_usages(**kwargs):
        usage = {
                  'servers_used': 10,
                  'vcpus_used': 10,
                  'ecus_used': 20,
                  'local_gb_used': 500,
                  'memory_gb_used': 40960,
                  'private_ips_used': 10,
                  'public_ips_used': 1,
                  'private_qos_used': 100,
                  'public_qos_used': 20
                }
        usage.update(**kwargs)
        return usage
