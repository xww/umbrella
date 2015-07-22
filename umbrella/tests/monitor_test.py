# Created on 2013-4-9
#
# @author: hzzhoushaoyu

import time

from umbrella import tests
from umbrella.db.sqlalchemy import models
from umbrella.monitor import monitor


def fake_time():
    return 1


class MonitorTest(tests.BaseTest):

    def setUp(self):
        tests.BaseTest.setUp(self)

    def test_format_metric(self):
        expected = {'dimensions': 'Platform=NVS',
                    'sampleCount': 1,
                    'value': 1,
                    'aggregationDimensions': '',
                    'createTime': long(time.time() * 1000),
                    'unit': 'unit',
                    'metricName': 'test'}
        result = monitor.format_metric(metric_name="test",
                                       dimensions="Platform=NVS",
                                       value=1, unit='unit')
        self.assertEqual(expected, result)

    def test_format_dimension(self):
        expected = "Platform=NVSPlatform"
        result = monitor.format_dimension(models.PLATFORM_LEVEL, "test")
        self.assertEqual(expected, result)

        expected = "host=test"
        result = monitor.format_dimension(models.HOST_LEVEL, "test")
        self.assertEqual(expected, result)

        expected = "AZ=test"
        result = monitor.format_dimension(models.AZ_LEVEL, "test")
        self.assertEqual(expected, result)

        expected = "user=test"
        result = monitor.format_dimension(models.USER_LEVEL, "test")
        self.assertEqual(expected, result)

    def test_convert_usages_to_metric(self):
        usages = {
                    'local_gb': {
                        'platform': [
                            {
                                'instance_id': 'uuid1',
                                'host': 'host1',
                                'project_id': 'xx1',
                                'local_gb': 40
                            },
                            {
                                'instance_id': 'uuid2',
                                'host': 'host2',
                                'project_id': 'xx2',
                                'local_gb': 20
                            }
                        ],
                        'platform_remainder': 964,
                        'platform_used': 60,
                        'platform_capacity': 1024
                    },
                    'servers': {
                        'platform': [
                            {
                                'instance_id': 'uuid1',
                                'host': 'host1',
                                'project_id': 'xx1',
                                'used': 1
                            },
                            {
                                'instance_id': 'uuid2',
                                'host': 'host2',
                                'project_id': 'xx2',
                                'used': 1
                            }
                        ],
                        'platform_used': 2
                    }
                }
        result = monitor.convert_usages_to_metric(usages,
                                                  models.PLATFORM_LEVEL)
        t = long(time.time() * 1000)
        expected = [
                    {
                        'dimensions': 'Platform=NVSPlatform',
                        'sampleCount': 1,
                        'value': 964,
                        'aggregationDimensions': '',
                        'createTime': t,
                        'unit': 'Gigabytes',
                        'metricName': 'remain_local_gb'
                    },
                    {
                        'dimensions': 'Platform=NVSPlatform',
                        'sampleCount': 1,
                        'value': 60,
                        'aggregationDimensions': '',
                        'createTime': t,
                        'unit': 'Gigabytes',
                        'metricName': 'local_gb'
                    },
                    {
                        'dimensions': 'Platform=NVSPlatform',
                        'sampleCount': 1,
                        'value': 1024,
                        'aggregationDimensions': '',
                        'createTime': t,
                        'unit': 'Gigabytes',
                        'metricName': 'total_local_gb'
                    },
                    {
                        'dimensions': 'Platform=NVSPlatform',
                        'sampleCount': 1,
                        'value': 2,
                        'aggregationDimensions': '',
                        'createTime': t,
                        'unit': 'Count',
                        'metricName': 'servers'
                    }
                ]
        self.assertEqual(expected, result)

    def test_Monitor_string_to_sign(self):
        result = monitor.Monitor([]).string_to_sign("GET")
        self.assertEqual('GET\n/rest/V1/MetricData\n\nAccessKey=None&'
                         'MetricDatasJson={"metricDatas": []}'
                         '&Namespace=openstack&ProjectId=None\n',
                         result)

    def test_Monitor_generate_signature(self):
        result = monitor.Monitor([]).generate_signature("GET")
        self.assertEqual('qPdUlUAfaQ8dyD8NgqqTK6s0wICNZrdqj1vVfrB7Vjc=',
                         result)
