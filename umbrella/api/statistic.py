'''
Created on 2012-10-25

@author: hzzhoushaoyu
'''

from umbrella.api.list_operation import filter as list_filter
from umbrella.api.list_operation import sort as list_sort
from umbrella.common import exception
import umbrella.common.log as logging
from umbrella.common import utils
from umbrella.common import wsgi
from umbrella.common import timeutils
from umbrella.db.sqlalchemy import models
from umbrella.monitor import manager
from umbrella.monitor import monitor
from umbrella.openstack import api as ops_api
from umbrella.openstack import client


LOG = logging.getLogger(__name__)

DEFAULT_CHANGE_SINCE_SECONDS = 3600 * 24 * 30
USAGE_REQUEST_PATH = manager.USAGE_REQUEST_PATH
SERVERS_REQUEST_PATH = "/{tenant_id}/servers/detail"
Metric_Name_Mapping = monitor.Metric_Name_Mapping
format_dimension = monitor.format_dimension


class Controller(object):

    def _filter_detail_usage(self, req, usage):
        search_opts = {}
        search_opts.update(req.GET)
        show_detail = search_opts.get('show_detail', False)
        if not show_detail:
            for usage_unit in usage:
                result = usage[usage_unit].copy()
                for key in usage[usage_unit]:
                    if isinstance(usage[usage_unit][key], list):
                        result.pop(key, None)
                usage.update({usage_unit: result})

    def get_az_capacity(self, req, tenant_id, az_name):
        '''
        get capacity for some az
        '''
        az_capacity = {}
        auth_token = req.headers.get("x-auth-token")
        hosts_capacity = ops_api.get_hosts_capacity(tenant_id, auth_token)
        zones = ops_api.get_hosts_az(tenant_id, auth_token)
        if 'availability_zones' not in zones:
            LOG.warn("availability_zones does not exists in zones(%s)" % zones)
        zones = zones.get('availability_zones', [])
        az_hosts = []
        for zone in zones:
            if az_name == zone['zoneName']:
                az_hosts = zone['hosts']
                break
        for hostname in hosts_capacity.keys():
            if hostname in az_hosts:
                host_capacity = hosts_capacity.get(hostname, {})
                if not az_capacity:
                    az_capacity.update(host_capacity)
                else:
                    for item in az_capacity.keys():
                        az_capacity[item] += host_capacity.get(item, 0)

        return az_capacity

    @utils.require_admin_context
    @utils.convert_mem_from_mb_to_gb
    def list_az_usage(self, req, tenant_id, az_name):
        '''
        List az usage.
        '''
        def _map_capacity_key(resource_key):
            mapped_key = {
                'ecus_capacity': 'ecus',
                'ecus_used': 'ecus_used',
                'local_gb_capacity': 'disk_gb',
                'local_gb_used': 'local_gb_used',
                'memory_mb_capacity': 'memory_mb',
                'memory_mb_used': 'memory_mb_used',
                'private_qos_capacity': 'private_network_qos_mbps',
                'private_qos_used': 'private_qos_used',
                'public_qos_capacity': 'public_network_qos_mbps',
                'public_qos_used': 'public_qos_used',
                'servers_used': 'servers_used',
                'vcpus_used': 'vcpus_used',
            }
            return mapped_key.get(resource_key, None)

        result = []
        m = manager.Manager()
        usages = m.request_usages(models.AZ_LEVEL, az_name)
        for values in usages:
            # Add statistic for az with no vms.
            az_capacity = self.get_az_capacity(req, tenant_id, az_name)
            for key in values.keys():
                if values[key]:
                    continue
                capacity_key = "%s_capacity" % key
                used_key = "%s_used" % key
                capacity = az_capacity.get(_map_capacity_key(capacity_key), 0)
                used = az_capacity.get(_map_capacity_key(used_key), 0)
                remainder = capacity - used
                if key != 'servers' and key != 'vcpus':
                    values[key] = {
                        az_name: [],
                        "%s_capacity" % az_name: capacity,
                        "%s_remainder" % az_name: remainder,
                        "%s_used" % az_name: used
                    }
                else:
                    values[key] = {
                        az_name: [],
                        "%s_used" % az_name: used
                    }

            self._filter_detail_usage(req, values)
            filter_usages = values
        for name in filter_usages:
            result.append(self._build_usage_for_history(name,
                                        filter_usages[name], models.AZ_LEVEL))
        return result

    @utils.require_admin_context
    @utils.convert_mem_from_mb_to_gb
    def index(self, req, tenant_id):
        '''
        list platform usage
        '''
        m = manager.Manager()
        usages = m.request_usages(models.PLATFORM_LEVEL)
        for values in usages:
            self._filter_detail_usage(req, values)
            # NOTE(hzzhoushaoyu): NO detail result may look like
            #{"memory_mb": {
            #               "platform_remainder": 4027,
            #               "platform_used": 4,
            #               "platform_capacity": 4031
            #               },
            # "private_qos": {
            #                 "platform_remainder": 1000,
            #                 "platform_used": 0,
            #                 "platform_capacity": 1000
            #                 },
            # "xxx": {
            #         "platform_remainder": 1000,
            #         "platform_used": 0,
            #         "platform_capacity": 1000
            #         }
            # }
            return values

    @utils.require_admin_context
    @utils.convert_mem_from_mb_to_gb
    def list_platform_usage(self, req, tenant_id):
        '''
        List platform usage version 2.
        To adapt to usage history data structure.
        '''
        result = []
        # NOTE(hzrandd): Do not call the interface 'index',which is called for
        # the interface statistics. so fix it like this:
        m = manager.Manager()
        usages = m.request_usages(models.PLATFORM_LEVEL)
        for values in usages:
            self._filter_detail_usage(req, values)
        for name in values:
            result.append(self._build_usage_for_history(name, values[name]))
        return result

    def _build_usage_for_history(self, name, usage,
                                 level=models.PLATFORM_LEVEL):
        '''
        build usage which may look like
        {
            "name": "current usage name",
            "values": [
                {
                    "metricName": "1-object-count",
                    "dimension": "cluster=1",
                    "currentValue": "234",
                    "statistics": "sum/average",
                    "description": " description for current metric " ,
                  " source ": 0
                }
            ]
        }
        '''
        # NOTE(hzzhoushaoyu): mapped_name and mapped_description is used for
        # extension. If name is not satisfied for result, convert them here.
        def mapped_name(name):
            return name

        def mapped_description(metricName):
            return metricName

        result = dict(name=mapped_name(name))
        values = []
        for key in usage:
            value = {}
            if key.endswith('_used'):
                metric_name = Metric_Name_Mapping[name]
                dimension = format_dimension(level, key.replace('_used', ''))
            elif key.endswith('_capacity'):
                metric_name = 'total_%s' % Metric_Name_Mapping[name]
                dimension = format_dimension(level,
                                             key.replace('_capacity', ''))
            elif key.endswith('_remainder'):
                metric_name = 'remain_%s' % Metric_Name_Mapping[name]
                dimension = format_dimension(level,
                                             key.replace('_remainder', ''))
            else:
                LOG.warn("Cannot recognize key %s" % key)
                continue
            value.update(metricName=metric_name)
            value.update(dimension=dimension)
            value.update(currentValue=usage[key])
            value.update(statistics="maximum")
            value.update(description=mapped_description(metric_name))
            value.update(source=0)
            values.append(value)
        result.update(values=values)
        return result

    def _construct_usage(self, usages):
        '''
            usages as sample below
                {
                    "ecus": {
                        "host1": [
                            {
                                "ecus": 10,
                                "unit": "host1",
                                "instance_id": "uuid1",
                                "project_id": "xx1"
                            }
                        ],
                        "host1_used": 10,
                        "host2": [
                            {
                                "ecus": 5,
                                "unit": "host2",
                                "instance_id": "uuid2",
                                "project_id": "xx2"
                            }
                        ],
                        "host2_used": 5
                    }
                }
            return value as sample below:
                {
                    "hosts": [
                    {
                        "hostname": "host1",
                        "local_gb_used": 40,
                        "memory_mb_used": 128,
                        "private_ips_used": 1,
                        "private_qos_used": 123,
                        "public_ips_used": 1,
                        "public_qos_used": 123,
                        "servers_used": 1,
                        "vcpus_used": 1
                    }]
                }
        '''
        # change usage key to unit key.
        # such as {ecus: {host1_used: 10}} to {hostname: host1, ecus_used: 10}
        items = {}
        for item in usages:  # as ecus in sample
            for unit in usages[item]:  # as host1 in sample
                if unit is None:
                    continue
                if type(usages[item][unit]) is list and unit not in items:
                    items.update({
                          unit: {
                            "%s_used" % item: usages[item]["%s_used" % unit]
                            }
                              })
                elif type(usages[item][unit]) is list:
                    items[unit].update({
                            "%s_used" % item: usages[item]["%s_used" % unit]})
        return items

    @utils.require_admin_context
    @utils.convert_mem_from_mb_to_gb
    def show_by_host(self, req, tenant_id):
        '''
        list platform usage
        '''
        def get_zone_by_host(zones, host):
            for zone in zones:
                if host in zone['hosts']:
                    return zone['zoneName']
        auth_token = req.headers.get("x-auth-token")
        m = manager.Manager()
        usages = m.request_usages(models.HOST_LEVEL)
        hosts_capacity = ops_api.get_hosts_capacity(tenant_id, auth_token)
        zones = ops_api.get_hosts_az(tenant_id, auth_token)
        if 'availability_zones' not in zones:
            LOG.warn("availability_zones does not exists in zones(%s)" % zones)
        zones = zones.get('availability_zones', [])
        for v in usages:
            # NOTE(hzzhoushaoyu): usages is a iterative value and here is only
            # one item.
            items = self._construct_usage(v)
            result = []
            for hostname in items:
                value = items[hostname]
                value.update(hostname=hostname)
                value.update(hosts_capacity.get(hostname, {}))
                zone_name = get_zone_by_host(zones, hostname)
                value.update(availability_zone=zone_name)
                # FIXME : This is a little ugly. when instances in the host
                #         doesn't use any floating ip, we need to set the
                #         ips_used number to 0. Currently I can't find a much
                #         proper place to do this thing.
                if 'private_ips_used' not in value.keys():
                    value.update(private_ips_used=0)
                if 'public_ips_used' not in value.keys():
                    value.update(public_ips_used=0)
                result.append(value)

            # Add statistics for hosts with no vms.
            for hostname in hosts_capacity.keys():
                already_counted = False
                for value in result:
                    if value['hostname'] == hostname:
                        already_counted = True
                        break
                if not already_counted:
                    value = {}
                    value.update(hostname=hostname)
                    value.update(hosts_capacity.get(hostname, {}))
                    value.update(private_ips_used=0)
                    value.update(public_ips_used=0)
                    zone_name = get_zone_by_host(zones, hostname)
                    value.update(availability_zone=zone_name)
                    result.append(value)

            result = list_filter.filter_host_usages(req, result)
            result = list_sort.sort_host_usage(req, result)
            return dict(hosts=result)

    @utils.require_admin_context
    @utils.convert_mem_from_mb_to_gb
    def show_by_tenant(self, req, tenant_id):
        '''
        list tenant usage
        '''
        m = manager.Manager()
        usages = m.request_usages(models.USER_LEVEL)
        for v in usages:
            items = self._construct_usage(v)
            result = []
            for k in items:
                value = items[k]
                value.update(tenant_id=k)
                result.append(value)
            result = list_filter.filter_tenants_usages(req, result)
            result = list_sort.sort_tenants_usage(req, result)
            return dict(tenants=result)

    def _statistic_instance_operation(self, req, tenant_id,
                                     start=None, end=None):
        '''
        list all instance include deleted and error,
        then statistic for operations.
        '''
        c = client.NovaClient()
        SERVERS_PATH = SERVERS_REQUEST_PATH.replace("{tenant_id}", tenant_id)
        params = {"all_tenants": True}
        if start:
            params.update({"changes-since": start})
        else:
            # default from a month ago.
            params.update({
                "changes-since": timeutils.seconds_ago(
                                            DEFAULT_CHANGE_SINCE_SECONDS)
                })
        params.update({"vm_state": "ERROR"})
        result, headers = c.response("GET",
                                     SERVERS_PATH,
                                     params,
                                     req.headers, req.body)
        successes = []
        errors = []
        for server in result["servers"]:
            created = server['created']
            if not _is_in_time(created, start, end):
                continue
            if server["OS-EXT-STS:vm_state"] == "error":
                fault = {}
                fault.update(tenant_id=server["tenant_id"])
                fault.update(uuid=server["id"])
                fault.update(name=server["name"])
                # FIXME(hzzhoushaoyu): fault code should be string
                # as filter should match string but int.
                if "fault" in server:
                    code = server["fault"].get("code", "500")
                    code = str(code)
                    server["fault"].update(code=code)
                    fault.update(server["fault"])
                    errors.append(fault)
                else:
                    fault.update({"message": "Unknow",
                             "code": "500",
                             "created": created})
                    errors.append(fault)
            else:
                # FIXME(hzzhoushaoyu) dead code.
                successes.append(server)
        return successes, errors

    def statistic_instance_success(self, req, tenant_id,
                                   start=None, end=None):
        '''
        list all success instance include deleted,
        then statistic for operations.
        '''
        success, error = self._statistic_instance_operation(req, tenant_id,
                                                            start, end)
        ret = {"SuccessInstanceOperation": len(success)}
        if start is not None:
            ret.update(start=start)
        if end is not None:
            ret.update(end=end)
        return ret

    @utils.log_func_exe_time
    def statistic_instance_error(self, req, tenant_id,
                                 start=None, end=None):
        '''
        list all error instance include deleted,
        then statistic for operations.
        '''
        success, error = self._statistic_instance_operation(req, tenant_id,
                                                            start, end)
        error = list_filter.filter_instance_error(req, error)
        error = list_sort.sort_instance_error(req, error)
        ret = {
                "ErrorInstanceOperation": len(error),
                "FaultList": error
                }
        if start is not None:
            ret.update(start=start)
        if end is not None:
            ret.update(end=end)
        return ret

    def _statistic_snapshot_operation(self, req, start=None, end=None):
        '''
        list all snapshots created,
        then statistic for operations.
        '''
        c = client.GlanceClient()
        params = {"is_public": "none"}
        if start:
            params.update({"changes-since": start})
        else:
            # default from a month ago.
            params.update({
                "changes-since":
                        timeutils.seconds_ago(DEFAULT_CHANGE_SINCE_SECONDS)
                })
        params.update({
                       "property-image_type": 'snapshot'
                       })
        result, headers = c.response("GET",
                                     "/images/detail",
                                     params,
                                     req.headers, req.body)
        error = []
        success = []
        for image in result['images']:
            created = image['created_at']
            if not _is_in_time(created, start, end):
                continue
            if image['checksum'] is None and\
                'image_type' in image['properties'] and\
                    image['properties']['image_type'] == 'snapshot':
                err_info = {
                            "id": image["id"],
                            "name": image["name"],
                            "owner": image["owner"],
                            "created": created,
                            "desc": "Instance %s create snapshot failed." %
                                        image['properties']['instance_uuid']
                            }
                error.append(err_info)
            else:
                # FIXME(hzzhoushaoyu) dead code.
                success.append(image)
        return success, error

    def statistic_snapshot_create_success(self, req, start=None, end=None):
        '''
        list all successfully created images,
        then statistic for operations.
        '''
        success, error = self._statistic_snapshot_operation(req, start, end)
        ret = {"SuccessSnapshotOperation": len(success)}
        if start is not None:
            ret.update(start=start)
        if end is not None:
            ret.update(end=end)
        return ret

    @utils.log_func_exe_time
    def statistic_snapshot_create_error(self, req, start=None, end=None):
        '''
        list all failed created images,
        then statistic for operations.
        '''
        success, error = self._statistic_snapshot_operation(req, start, end)
        error = list_filter.filter_snapshot_error(req, error)
        error = list_sort.sort_snapshot_error(req, error)
        ret = {
               "ErrorSnapshotOperation": len(error),
               "FaultList": error
               }
        if start is not None:
            ret.update(start=start)
        if end is not None:
            ret.update(end=end)
        return ret


class RequestDeserializer(wsgi.JSONRequestDeserializer):

    def _normalize_time(self, request):
        params = request.params.copy()
        start = params.pop("start", None)
        end = params.pop("end", None)

        try:
            start = timeutils.local_to_utc(
                            timeutils.timestamp_to_datetime(start)) \
                    if start is not None \
                    else timeutils.seconds_ago(DEFAULT_CHANGE_SINCE_SECONDS)
            end = timeutils.local_to_utc(
                            timeutils.timestamp_to_datetime(end)) \
                            if end is not None else None
        except ValueError:
            raise exception.Invalid(_("Not invalid datetime format."))

        query_params = {
                        "start": start,
                        "end": end
                        }

        return query_params

    def statistic_instance_success(self, request):
        return self._normalize_time(request)

    def statistic_instance_error(self, request):
        return self._normalize_time(request)

    def statistic_snapshot_create_success(self, request):
        return self._normalize_time(request)

    def statistic_snapshot_create_error(self, request):
        return self._normalize_time(request)


def normalize_time_str(time_str):
    try:
        # local time zone datetime format
        return timeutils.normalize_time(
                timeutils.local_to_utc(
                    timeutils.parse_strtime(time_str, "%Y-%m-%d %H:%M:%S")))
    except ValueError:
        # UTC+0 time zone datetime format or others
        return timeutils.normalize_time(
                timeutils.parse_isotime(time_str))


def _is_in_time(target_time, start, end):
    if start is not None:
        if (normalize_time_str(target_time) - \
                        timeutils.normalize_time(start)).total_seconds() < 0:
            return False
    if end is not None:
        if (normalize_time_str(target_time) - \
                        timeutils.normalize_time(end)).total_seconds() > 0:
            return False
    return True


def create_resource():
    """Servers resource factory method"""
    return wsgi.Resource(Controller(), deserializer=RequestDeserializer())
