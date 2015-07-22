#
# Created on 2012-10-27
#
# @author: hzzhoushaoyu
#

import eventlet
from webob import exc

from umbrella.common import cfg
from umbrella.common import exception
import umbrella.common.log as logging
from umbrella.openstack import api
import umbrella.db.sqlalchemy.models as models
from umbrella.monitor import alarm
from umbrella.monitor import monitor
from umbrella.common import utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
alarm_opts = [
              cfg.BoolOpt("need_alarm", default=False)
              ]
CONF.register_opts(alarm_opts)

USAGE_REQUEST_PATH = "/{tenant_id}/os-simple-tenant-usage"
HOST_REQUEST_PATH = "/{tenant_id}/os-hosts"
FLOAT_IP_REQUEST_PATH = "/{tenant_id}/os-floating-ips-search"


def retry_with_new_token(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except exception.NotAuthenticated:
            LOG.info(_("Request new AUTH token and retry."))
            api.request_admin_token(search_cache=False)
            return fn(*args, **kwargs)
    return wrapper


class Manager(object):
    '''
    manage class for usage monitor
    '''

    def __init__(self):
        self.usage = None
        self.levels = [models.PLATFORM_LEVEL, models.HOST_LEVEL,
                       models.USER_LEVEL]

    @retry_with_new_token
    def get_item(self, data_key, used_key, level=models.PLATFORM_LEVEL,
                 need_capacity=True, az_name=None):
        '''
        calculate usage for specify resource such as memory.
        :param data_key: key in usages for usage data list.
        :param used_key: key in each usage data for used calculating.
        :param token: admin auth token.
        :param level: calculating level(models.PLATFORM/HOST/AZ/USER_LEVEL)
        result[{data_key}] should look like:
        {"memory_mb": {"memory_mb": [
                        {
                         "project_id": "xx1",
                         "instance_id": "uuid1",
                         "host": "host1",
                         "memory_mb": 128
                         },
                        {
                         "project_id": "xx2",
                         "instance_id": "uuid2",
                         "host": "host2",
                         "memory_mb": 256
                         },
                        ]
                       },
          "capacity": 10240}

        :return : sample as:
            {
            'memory_mb': {
                'platform': [
                    {
                        'instance_id': 'uuid1',
                        'memory_mb': 128,
                        'host': 'host1',
                        'project_id': 'xx1'
                    },
                    {
                        'instance_id': 'uuid2',
                        'memory_mb': 256,
                        'host': 'host2',
                        'project_id': 'xx2'
                    }
                ],
                'platform_used': 384
            }
        }
        '''
        token = api.request_admin_token()
        if self.usage is None:
            try:
                result = api.get_usages(token['tenant']['id'], token['id'])
            except KeyError:
                LOG.exception(_("get usage failed."))
                raise exc.HTTPFailedDependency(
                                    _("Nova or Keystone verstion not match."))
            self.usage = result
        else:
            result = self.usage
        try:
            item_usage = calc_item(result[data_key][data_key], level, used_key)
            zone_usage = {}
            if level == models.AZ_LEVEL and az_name != None:
                for i in range(len(item_usage)):
                    az_key = item_usage.keys()[i]
                    # filter usage info by az_name
                    if az_key == az_name:
                        zone_usage.update({az_key: item_usage.get(az_key)})
                    elif az_key == "%s_used" % az_name:
                        zone_usage.update({az_key: item_usage.get(az_key)})
                item_usage = {}
                item_usage.update(zone_usage)
            else:
                zone_usage.update(item_usage)

            if not need_capacity:
                return item_usage
            # calculate platform capacity and remainder.
            item_capacity = result[data_key]['capacity']
            if level == models.PLATFORM_LEVEL:
                # calculate remainder resource for platform level
                calc_resource_remainder(item_usage, item_capacity,
                                        None)
                item_usage.update({'platform_capacity': item_capacity})
            if level == models.AZ_LEVEL:
                zones = api.get_hosts_az(token['tenant']['id'], token['id'])
                zones = zones['availability_zones']
                host_capacities = api.get_hosts_capacity(token['tenant']['id'],
                                                         token['id'])
                mapped_key = {
                    'ecus': 'ecus',
                    'local_gb': 'disk_gb',
                    'memory_mb': 'memory_mb',
                    'public_qos': 'public_network_qos_mbps',
                    'private_qos': 'private_network_qos_mbps'
                }

                for i in range(len(item_usage)):
                    az = item_usage.keys()[i]
                    if "_used" in az:
                        continue
                    capacity = 0
                    for zone in zones:
                        if zone['zoneName'] == az:
                            hosts = zone['hosts']
                    for host in hosts:
                        host_capacity = host_capacities[host].get(
                                                    mapped_key[data_key], 0)
                        capacity += host_capacity
                    zone_usage.update({"%s_capacity" % az: capacity})
                    calc_resource_remainder(zone_usage, capacity,
                                            None, unit=az)
                # AZ item_usage data structure sample as
                #{
                #    u'nova_capacity': 1000,
                #    u'nova': [
                #        {
                #            u'instance_id': u'71c5ab41-b8e7-4d40-8439',
                #            u'host': u'10-120-240-46',
                #            u'project_id': u'dc32392af0ae4a098fb7235760077f',
                #            u'type': u'public'
                #        },
                #        {
                #            u'instance_id': u'0f6c6354-3d92-45a5-8221',
                #            u'host': u'10-120-240-46',
                #            u'project_id': u'dc32392af0ae4a098fb7235760077',
                #            u'type': u'public'
                #        }
                #    ],
                #    u'nova_used': 0
                #}
                item_usage = {}
                item_usage.update(zone_usage)
            return item_usage
        except KeyError:
            LOG.exception(_("Calculate %s usage failed.") % data_key)
            raise exception.ServiceUnavailable(_("Nova version not match."))

    def get_vcpus(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of local disk.
        sample to see self.get_item()
        '''
        return dict(vcpus=self.get_item("vcpus", "vcpus",
                                            level, False, az_name))

    def get_servers(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of local disk.
        sample to see self.get_item()
        '''
        return dict(servers=self.get_item("servers", "used",
                                            level, False, az_name))

    def get_local_gb(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of local disk.
        sample to see self.get_item()
        '''
        return dict(local_gb=self.get_item("local_gb", "local_gb",
                                            level, True, az_name))

    def get_memory_mb(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of memory.
        sample to see self.get_item()
        '''
        return dict(memory_mb=self.get_item("memory_mb", "memory_mb",
                                            level, True, az_name))

    def get_floating_ips(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of public and private floating IPs.
        sample to see self.get_item()
        '''
        pri_ips = dict(private_ips=self.get_item("private_ips", "used",
                                            level, True, az_name))
        pub_ips = dict(public_ips=self.get_item("public_ips", "used",
                                            level, True, az_name))
        result = {}
        result.update(pri_ips)
        result.update(pub_ips)
        return result

    def get_network_qos(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of public and private network QoS.
        sample to see self.get_item()
        '''
        pri_qos = dict(private_qos=self.get_item("private_qos", "rate",
                                            level, True, az_name))
        pub_qos = dict(public_qos=self.get_item("public_qos", "rate",
                                            level, True, az_name))
        result = {}
        result.update(pri_qos)
        result.update(pub_qos)
        return result

    def get_ecus(self, level=models.PLATFORM_LEVEL, az_name=None):
        '''
        return MetaData and statistic data of ECU.
        sample to see self.get_item()
        '''
        return dict(ecus=self.get_item("ecus", "ecus",
                                        level, True, az_name))

    def request_usages(self, level, az_name=None):
        '''
        roll polling for all URLs of specify level and yield usages
        :return : sample as:
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
        '''
        usages = {}
        if level == models.AZ_LEVEL:
            resource_methods = [self.get_ecus,
                                self.get_local_gb, self.get_memory_mb,
                                self.get_network_qos, self.get_servers,
                                self.get_vcpus]
        else:
            resource_methods = [self.get_ecus, self.get_floating_ips,
                                self.get_local_gb, self.get_memory_mb,
                                self.get_network_qos, self.get_servers,
                                self.get_vcpus]

        for resource_method in resource_methods:
            usages.update(resource_method(level, az_name))
        yield usages

    def check_alarm(self, level, usage):
        '''
        check whether need alarm for all of specify level usages
        '''
        try:
            if level == models.PLATFORM_LEVEL:
                alarm.AlarmCheck().check_threshold(level, usage)
        except exception.UmbrellaException:
            LOG.debug(_("NO alarms because of NO implementation."))

    def periodic_tasks(self, level):
        '''
        periodic task to get usage from openstack and check warning
        '''
        LOG.debug("looping calling get usage from openstack for level %s...." %
                  level)
        for usage in self.request_usages(level):
            metric_list = monitor.convert_usages_to_metric(usage, level)
            utils.convert_mem_to_gb_for_monitor(metric_list)
            if CONF.need_alarm:
                LOG.debug(_("alarm for level %s."), level)
                eventlet.spawn_n(self.check_alarm, level, usage)
            eventlet.spawn_n(self.post_monitor, level, metric_list)

    def post_monitor(self, level, metric_list):
        '''
        post statistic usage data to monitor
        '''
        LOG.info(_("posting usage of level %(level)s to monitor..."),
                  locals())
        m = monitor.Monitor(metric_list)
        m.post()


def calc_resource_remainder(usage, capacity, key, unit='platform'):
    if key is None:
        used = int(
            usage['%s_used' % unit])
    else:
        used = int(
            usage[key]['%s_used' % unit])
    remainder = capacity - used
    if key is None:
        usage.update(
                {'%s_remainder' % unit: remainder})
    else:
        usage[key].update(
                {'%s_remainder' % unit: remainder})


def calc_item(items, level, key):
    '''
    :param items: A list of all items, samples as:
        [
          {
           "tenant_id": "xx1",
           "instance_id": "uuid1",
           "host": "host1",
           "{key}": 10
           },
          {
           "tenant_id": "xx2",
           "instance_id": "uuid2",
           "host": "host2",
           "{key}": 5
           }
      ]
    :param level: specify which level to calcute usage
    :param key: specify which key is to be used as usage
    return sample as:
    {u'10-120-240-46': [
                        {u'instance_id': u'71c5ab41-b8e7',
                         u'host': u'10-120-240-46',
                         u'project_id': u'dc32392af0ae4a098fb7235760077fa6',
                         u'local_gb': 10},
                        {u'instance_id': u'0f6c6354-3d92-45a5',
                         u'host': u'10-120-240-46',
                         u'project_id': u'dc32392af0ae4a098fb7235760077fa6',
                         u'local_gb': 10}],
    u'10-120-240-46_used': 20}
    '''
    item_classify = {}
    zones = None
    if level == models.AZ_LEVEL:
        token = api.request_admin_token()
        all_az = api.get_hosts_az(token['tenant']['id'], token['id'])
        try:
            zones = all_az['availability_zones']
        except:
            LOG.exception(_("Get AZ information error."))
            raise

    for item in items:
        # NOTE(hzzhoushaoyu): item sample as:
        # {u'instance_id': u'0f6c6354-3d92-45a5-8221-aa0035c07f43',
        #  u'host': u'10-120-240-46', u'local_gb': 10,
        #  u'project_id': u'dc32392af0ae4a098fb7235760077fa6'}
        if not item:
            continue
        if level == models.PLATFORM_LEVEL:
            classify_item(item, item_classify, "platform")
        elif level == models.HOST_LEVEL:
            host = _get_item_host(item)
            if host is None:
                continue
            classify_item(item, item_classify, host)
        elif level == models.AZ_LEVEL:
            for zone in zones:
                if 'hosts' not in zone:
                    LOG.warn(_("Zone information does not contain hosts."))
                hosts = zone.get('hosts', [])
                host = _get_item_host(item)
                if host in hosts:
                    classify_item(item, item_classify, zone['zoneName'])
        elif level == models.USER_LEVEL:
            classify_item(item, item_classify, item['project_id'])
    if len(items) == 0 and level == models.PLATFORM_LEVEL:
        item_classify = {"platform": []}
    analysis_item_used(item_classify, key)
    return item_classify


def _get_item_host(item):
    host = item.get('host', None)
    if host is None:
        host = item.get('host_id', None)
    return host


def classify_item(item, item_classify, key):
    '''
    classify item to specify platform/host/user for diffrent levels.
    '''
    list = item_classify.get(key, [])
    list.append(item)
    item_classify.update({key: list})


def analysis_item_used(item_dict, key):
    '''
    :param item_dict: dict obj look like {'platform': [xxx]}
    '''
    item_cacl = {}
    for k in item_dict:
        if k is None:
            continue
        item_used = 0
        for item in item_dict[k]:
            if item and key in item:
                item_used += int(item[key])
        item_cacl.update({"%s_used" % k: item_used})
    item_dict.update(item_cacl)
