#
# Created on 2013-1-1
#
# @author: zhoushaoyu
#

from umbrella.common import exception
import umbrella.common.log as logging
from umbrella.common import utils

LOG = logging.getLogger(__name__)

valid_sort_dir = ['asc', 'desc']


def sort_key_for_ip_wrapped(sort_key):
    '''
    Use to sort IP as integer tuple.
    '''
    def sort_key_for_ip(item):
        result = []
        try:
            ips = utils.get_value_by_key(item, sort_key)
            if not ips:
                return result
            if not isinstance(ips, list):
                return utils.convert_IP_to_tuple(ips)
            for ip in ips:
                result.append(utils.convert_IP_to_tuple(ip))
        except (AttributeError, TypeError, ValueError):
            LOG.exception("Error occurred when sort by IP.")
            raise exception.InvalidIP(message=_("IP which is sorting"
                                                " is not valid."))
        return result
    return sort_key_for_ip


def sort_items(items, sort_key, sort_dir):
    if sort_key is None:
        return items
    if sort_dir not in valid_sort_dir:
        raise exception.InvalidSortKey('sort dir only support '
                                       'asc/desc with case insensitive.')
    return sorted(items,
                  key=lambda item:
                        utils.get_lower_case_value_by_key(item, sort_key),
                  reverse=(sort_dir == 'desc'))


def map_opts_and_sort(req, items, mapped_method, sort_method=None):
    search_opts = {}
    search_opts.update(req.GET)
    sort_key = search_opts.pop('umbrella_sort_key', None)
    sort_key = mapped_method(sort_key)
    sort_dir = search_opts.pop('umbrella_sort_dir', 'asc')
    sort_dir = sort_dir.lower()
    sort_method = sort_method or sort_items
    return sort_method(items, sort_key, sort_dir)


def sort_servers(req, servers):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'tenant_id',
                      'tenant_name': 'tenant_name',
                      'name': 'name',
                      'host': 'OS-EXT-SRV-ATTR:host',
                      'fixed_ip': 'fixed_ips/#list/addr',
                      'nbs': 'nbs',
                      'status': 'status'
                      }
        return mapped_key.get(sort_key, None)

    def _sort_servers(servers, sort_key, sort_dir):
        if sort_key is None:
            return servers
        if sort_key != 'fixed_ips/#list/addr':
            return sort_items(servers, sort_key, sort_dir)
        return sorted(servers,
                      key=sort_key_for_ip_wrapped(sort_key),
                      reverse=(sort_dir == 'desc'))

    return map_opts_and_sort(req, servers, _map_sort_key, _sort_servers)


def sort_images(req, images):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'owner',
                      'tenant_name': 'owner_name',
                      'name': 'name',
                      'id': 'id',
                      'description': 'properties/description',
                      'size': 'size',
                      'status': 'status'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, images, _map_sort_key)


def sort_security_groups(req, groups):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'tenant_id',
                      'tenant_name': 'tenant_name',
                      'name': 'name',
                      'description': 'description'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, groups, _map_sort_key)


def sort_floating_ips(req, ips):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'project_id',
                      'tenant_name': 'project_name',
                      'ip': 'ip',
                      'type': 'type',
                      'pool': 'pool',
                      'instance_name': 'instance_name'
                      }
        return mapped_key.get(sort_key, None)

    def _sort_floating_ips(floating_ips, sort_key, sort_dir):
        if sort_key is None:
            return floating_ips
        if sort_key != 'ip':
            return sort_items(floating_ips, sort_key, sort_dir)
        return sorted(floating_ips,
                      key=sort_key_for_ip_wrapped(sort_key),
                      reverse=(sort_dir == 'desc'))

    return map_opts_and_sort(req, ips, _map_sort_key, _sort_floating_ips)


def sort_keypairs(req, keypairs):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'user_id',
                      'user_name': 'user_name',
                      'name': 'name',
                      'fingerprint': 'fingerprint',
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, keypairs, _map_sort_key)


def sort_quotas(req, quotas):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'tenant_id',
                      'tenant_name': 'tenant_name',
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, quotas, _map_sort_key)


def sort_instance_error(req, error):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'tenant_id',
                      'name': 'name',
                      'uuid': 'uuid',
                      'code': 'code',
                      'created': 'created',
                      'message': 'message'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, error, _map_sort_key)


def sort_snapshot_error(req, error):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'owner',
                      'name': 'name',
                      'id': 'id',
                      'created': 'created',
                      'desc': 'desc'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, error, _map_sort_key)


def sort_host_usage(req, usages):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'hostname': 'hostname',
                      'availability_zone': 'availability_zone',
                      'servers': 'servers_used',
                      'vcpus': 'vcpus_used',
                      'ecus': 'ecus_used',
                      'local_gb': 'local_gb_used',
                      'memory_gb': 'memory_gb_used',
                      'private_ips': 'private_ips_used',
                      'public_ips': 'public_ips_used',
                      'private_qos': 'private_qos_used',
                      'public_qos': 'public_qos_used'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, usages, _map_sort_key)


def sort_tenants_usage(req, usages):
    def _map_sort_key(sort_key):
        mapped_key = {
                      'tenantid': 'tenant_id',
                      'servers': 'servers_used',
                      'vcpus': 'vcpus_used',
                      'ecus': 'ecus_used',
                      'local_gb': 'local_gb_used',
                      'memory_gb': 'memory_gb_used',
                      'private_ips': 'private_ips_used',
                      'public_ips': 'public_ips_used',
                      'private_qos': 'private_qos_used',
                      'public_qos': 'public_qos_used'
                      }
        return mapped_key.get(sort_key, None)
    return map_opts_and_sort(req, usages, _map_sort_key)
