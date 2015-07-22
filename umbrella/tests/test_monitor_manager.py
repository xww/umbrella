# Created on 2013-4-9
#
# @author: hzzhoushaoyu
from umbrella import tests
from umbrella.db.sqlalchemy import models
from umbrella.monitor import manager


class ManagerTest(tests.BaseTest):
    def test_calc_resource_remainder(self):
        usage = {
                    'platform': [
                        {
                        'instance_id': 'uuid1',
                        'tenant_id': 'xx1',
                        'host': 'host1',
                        'key': 10
                        },
                        {
                        'instance_id': 'uuid2',
                        'tenant_id': 'xx2',
                        'host': 'host2',
                        'key': 5
                        }
                    ],
                    'platform_used': 15
                }
        manager.calc_resource_remainder(usage, 100, None)
        self.assertEqual({
                            'platform': [
                                {
                                'instance_id': 'uuid1',
                                'tenant_id': 'xx1',
                                'host': 'host1',
                                'key': 10
                                },
                                {
                                'instance_id': 'uuid2',
                                'tenant_id': 'xx2',
                                'host': 'host2',
                                'key': 5
                                }
                            ],
                          'platform_remainder': 85,
                          'platform_used': 15
                        }, usage)

    def test_calc_item(self):
        expected = {
                    'platform': [
                        {
                            'instance_id': 'uuid1',
                            'tenant_id': 'xx1',
                            'host': 'host1',
                            'key': 10
                        },
                        {
                            'instance_id': 'uuid2',
                            'tenant_id': 'xx2',
                            'host': 'host2',
                            'key': 5
                        }
                    ],
                    'platform_used': 15
                }
        result = manager.calc_item([
                                      {
                                       "tenant_id": "xx1",
                                       "instance_id": "uuid1",
                                       "host": "host1",
                                       "key": 10
                                       },
                                      {
                                       "tenant_id": "xx2",
                                       "instance_id": "uuid2",
                                       "host": "host2",
                                       "key": 5
                                       }
                                  ],
                                models.PLATFORM_LEVEL, 'key')
        self.assertEqual(expected, result)
