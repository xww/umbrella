'''
Created on 2012-10-31

@author: hzzhoushaoyu
'''
import httplib
import hmac
import urllib
import hashlib
import json
import time

from umbrella.common import cfg
import umbrella.common.log as logging
from umbrella.db.sqlalchemy import models

CONF = cfg.CONF

opts = [
        cfg.StrOpt("monitor_service_host"),
        cfg.StrOpt("monitor_service_port"),
        cfg.StrOpt("monitor_service_path", default="/rest/V1/MetricData"),
        cfg.StrOpt("admin_project_id"),
        cfg.StrOpt("monitor_platform", default="NVSPlatform"),
        cfg.StrOpt("monitor_namespace", default="openstack"),
        cfg.StrOpt("monitor_access_key"),
        cfg.StrOpt("monitor_access_secret")
        ]

CONF.register_opts(opts)

UNIT_COUNT = 'Count'
UNIT_MB = 'Megabytes'
UNIT_GB = 'Gigabytes'

# Note(hzzhoushaoyu): metric that will be pushed to monitor and ITS unit.
# Note(hzrandd): modfiy the 'memory_mb' information from UNIT_MB to UNIT_GB.
# but do not modfiy the 'memory_mb' to 'memory_gb' to keep the api Consistency.
UNIT_KEY_IN_USAGE = {
                     'private_qos': UNIT_MB,
                     'public_qos': UNIT_MB,
                     'private_ips': UNIT_COUNT,
                     'public_ips': UNIT_COUNT,
                     'ecus': UNIT_COUNT,
                     'servers': UNIT_COUNT,
                     'vcpus': UNIT_COUNT,
                     'memory_mb': UNIT_GB,
                     'local_gb': UNIT_GB
                     }

# mapping key is key in usage, mapping value is metric name of 'used'.
# platform capacity should be like 'total_{mapping_value}'
# platform remainder should be like 'remain_{mapping_value}'
Metric_Name_Mapping = {
                        'private_qos': 'private_netqos',
                        'public_qos': 'public_netqos',
                        'private_ips': 'private_floating_ips',
                        'public_ips': 'public_floating_ips',
                        'ecus': 'ecus',
                        'servers': 'servers',
                        'vcpus': 'vcpus',
                        'memory_mb': 'memory_mb',
                        'local_gb': 'local_gb'
                       }

LOG = logging.getLogger(__name__)


def format_metric(metric_name, dimensions, value, unit):
    metric_datas = {
                    'metricName': metric_name,
                    'dimensions': dimensions,
                    'aggregationDimensions': '',
                    'value': value,
                    'sampleCount': 1,
                    'createTime': long(time.time() * 1000),
                    'unit': unit
                    }
    return metric_datas


def format_dimension(level, key):
    if level == models.PLATFORM_LEVEL:
        dimension = 'Platform=%s' % CONF.monitor_platform
    elif level == models.HOST_LEVEL:
        dimension = 'host=%s' % key
    elif level == models.AZ_LEVEL:
        dimension = 'AZ=%s' % key
    elif level == models.USER_LEVEL:
        dimension = 'user=%s' % key
    else:
        dimension = None
    return dimension


def convert_usages_to_metric(usages, level):
    '''
    Convert xxx_remainder, xxx_used, xxx_capacity to metric construct.
    :param usages: usages dict Object. sample as:
    {
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
    :return : return converted metric list.
    '''
    metric_list = []
    for usage_name in usages:
        for key in usages[usage_name]:
            if key is None:
                continue
            if key.endswith('_used'):
                metric_name = Metric_Name_Mapping[usage_name]
                dimension = format_dimension(level, key.replace('_used', ''))
            elif key.endswith('_capacity'):
                metric_name = 'total_%s' % Metric_Name_Mapping[usage_name]
                dimension = format_dimension(level,
                                             key.replace('_capacity', ''))
            elif key.endswith('_remainder'):
                metric_name = 'remain_%s' % Metric_Name_Mapping[usage_name]
                dimension = format_dimension(level,
                                             key.replace('_remainder', ''))
            else:
                continue
            if dimension is None:
                LOG.info(_("LEVEL NOT FOUND. "
                           "Dimension could not be recognized."))
                continue
            if usage_name not in UNIT_KEY_IN_USAGE:
                LOG.info(_("%(usages) has no key %(key)..."), locals())
                unit = UNIT_COUNT
            else:
                unit = UNIT_KEY_IN_USAGE[usage_name]
            metric_item = format_metric(metric_name, dimension,
                                        usages[usage_name][key], unit)
            metric_list.append(metric_item)
    return metric_list


class Monitor(object):
    '''
        Send data to monitor server by accesskey authorization.
    '''
    def __init__(self, metric_list):
        self.url = "%s:%s" % (CONF.monitor_service_host,
                                CONF.monitor_service_port)
        self.requestURI = CONF.monitor_service_path
        self.headers = {'Content-type': 'application/x-www-form-urlencoded'}
        self.project_id = CONF.admin_project_id
        self.namespace = CONF.monitor_namespace
        self.access_key = CONF.monitor_access_key
        self.access_secret = CONF.monitor_access_secret
        self.metric_datas_json = json.dumps(dict(metricDatas=metric_list))

    def post(self):
        '''
            Send monitor data to collect server by POST request.
        '''
        params = urllib.urlencode({
                'ProjectId': self.project_id,
                'Namespace': self.namespace,
                'MetricDatasJson': self.metric_datas_json,
                'AccessKey': self.access_key,
                'Signature': self.generate_signature('POST')
        })
        LOG.debug(_("post to monitor: %s") % self.metric_datas_json)
        conn = httplib.HTTPConnection(self.url)
        conn.request('POST', self.requestURI, params, self.headers)
        httpres = conn.getresponse()
        if httpres.status != 200:
            content = httpres.read()
            LOG.error(_("request monitor error (status:%s):%s...%s"),
                      httpres.status, httpres.reason, content.decode('utf8'))
        conn.close()
        LOG.info(_("Post usages to monitor successfully!"))

    def string_to_sign(self, http_method):
        '''
            Generate stringToSign for signature.
        '''
        CanonicalizedHeaders = ''
        CanonicalizedResources = 'AccessKey=%s&MetricDatasJson=%s' \
                                    '&Namespace=%s&ProjectId=%s' % \
                                (self.access_key, self.metric_datas_json,
                                    self.namespace, self.project_id)

        StringToSign = '%s\n%s\n%s\n%s\n' % \
                      (http_method, self.requestURI,
                        CanonicalizedHeaders, CanonicalizedResources)

        return StringToSign

    def generate_signature(self, http_method):
        '''
            Generate signature for authorization.
            Use hmac SHA-256 to calculate signature string and encode
            into base64.
            @return String
        '''
        stringToSign = self.string_to_sign(http_method)
        hashed = hmac.new(str(self.access_secret), stringToSign,
                          hashlib.sha256)
        s = hashed.digest()
        signature = s.encode('base64').rstrip()
        return signature
