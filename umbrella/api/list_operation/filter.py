#
# Created on Dec 20, 2012
#
# @author: hzzhoushaoyu
#

from umbrella.common import exception
import umbrella.common.log as logging
from umbrella.common import utils
from umbrella.openstack import api as ops_api

LOG = logging.getLogger(__name__)
TRUE_STR_LIST = ["1", "true", "y"]


def and_(items, keys, values):
    '''
    :param items: items which are to be searched
                  for matching all values.
    :param keys: keys which to be match,
                 key in values and items should be the same.
    :param values: values which to be match
    '''
    result = []
    # Note(hzrandd):check the values should search or not,
    # to deal with the sort_key(s) which is(are) error.
    # such as : 'hos'or 'hosts', it likes 'host',
    # so return all the items for user.
    tag = False
    for k, v in values.items():
        if values[k] is not None:
            tag = True
            break
    if not tag:
        return items

    for item in items:
        matched = True
        for key in keys:
            # target is what user want
            target = values.get(key, None)
            if target is None:
                # No search for this key
                continue
            item_attr = utils.get_value_by_key(item, key)
            if item_attr is None:
                # item doesn't contain key
                LOG.warn(_("Item does not contain key %s.") % key)
                matched = False
                break
            elif isinstance(item_attr, list):
                # if get item_attr list from item,
                # compare each item_attr.
                # All not matched, the item is abandoned.
                one_match = False
                for each_value in item_attr:
                    if target.lower() == each_value.lower():
                        one_match = True
                        break
                if not one_match:
                    matched = False
                    break
            elif isinstance(item_attr, bool):
                if item_attr != (target.lower() in TRUE_STR_LIST):
                    matched = False
                    break
            elif target.lower() != item_attr.lower():
                # if item_attr is not None and not list,
                # compare with target.
                matched = False
                break
        if matched:
            result.append(item)
    return result


def or_(items, keys, value, tenantid_key, tenantid):
    '''
    specify keys in items and search match any key and value.
    '''
    LOG.debug(_("or_ for value %s and tenantid %s") % (value, tenantid))
    if value is None and tenantid is None:
        return items
    results = []
    for item in items:
        if tenantid is not None and tenantid in item.get(tenantid_key, None):
            # If tenantid is matched, add matched item
            # and no need for compare other keys.
            # Then continue to match other items.
            results.append(item)
            continue
        if value is None:
            # search only by tenant id
            continue
        for key in keys:
            item_attr = utils.get_value_by_key(item, key)
            if item_attr is None:
                LOG.debug(_("get value by key %s and return item_attr %s") %
                    (key, item_attr))
            elif isinstance(item_attr, list):
                # if get value list from item,
                # compare each value.
                # One matched. append the item.
                one_match = False
                for each_target in item_attr:
                    if value.lower() == each_target.lower():
                        one_match = True
                        break
                if one_match:
                    results.append(item)
                    break
            elif isinstance(item_attr, bool):
                if item_attr == (value.lower() in TRUE_STR_LIST):
                    results.append(item)
                    break
            elif value.lower() == item_attr.lower():
                # if item_attr is not none and not list
                # compare value.
                results.append(item)
                break
    return results


def filter_items(req, items, keys, tenant_id_key, values,
                 item_owner_id_key='tenantid'):
    '''
    :param req: Request Object
    :param items: item list to filter
    :param keys: keys relation with values to compare in each item
    :param tenant_id_key: tenant id key in each item
    :param values: key/value pairs that user specify to search
                   keys in values should be one of param {keys}
    :param item_owner_id_key: item owner id key in paramters of user required.
                              Here may be just for keypair user id, but others
                              are tenant id.
    '''
    search_opts = {}
    search_opts.update(req.GET)
    if 'relationship' not in search_opts:
        return items
    owner_id = search_opts.pop(item_owner_id_key, None)
    if search_opts['relationship'] == 'or':
        value = search_opts.pop("key", None)
        return or_(items, keys, value, tenant_id_key, owner_id)
    elif search_opts['relationship'] == 'and':
        and_keys = keys
        and_keys.append(tenant_id_key)
        values.update({tenant_id_key: owner_id})
        return and_(items, and_keys, values)
    else:
        raise exception.InvalidFilterItem(_("relationship doesn't "
                                       "support any key except 'and', 'or'."))


def filter_servers(req, servers):
    '''
    servers sample as:
    [{
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
        "tenant_id": "dc32392af0ae4a098fb7235760077fa6",
        "tenant_name": "admin",
        "updated": "2012-12-05T11:36:12Z",
        "user_id": "f2665c1140c54a03a98110cb86262ec3"
    }]

    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify server owner
                tenantname, specify owner tenant
                name, specify server name
                host, specify host name
                fixed_ip, specify IP
                status, specify status
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['name', 'OS-EXT-SRV-ATTR:host',
            'fixed_ips/#list/addr', 'status',
            'tenant_name']
    values = {}
    # Note(hzrandd): remove the sort_key start with 'umbrella_',
    # and check should search precisely match or not.
    support_params = ['tenant_name', 'name', 'host', 'fixed_ip', 'status']
    for params in support_params:
        if params in search_opts.keys():
            if params == 'host':
                values['OS-EXT-SRV-ATTR:host'] = search_opts[params]
            elif params == 'fixed_ip':
                values['fixed_ips/#list/addr'] = search_opts[params]
            else:
                values[params] = search_opts[params]
    return filter_items(req, servers, keys, 'tenant_id', values)


def filter_images(req, images):
    '''
    images sample as:
   [
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
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify image owner
                tenantname, specify image owner name
                id, specify image id
                name, specify image name
                status, specify image status
                desc, specify image property desc
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['name', 'id', 'properties/description', 'status', 'is_public',
            'owner_name']
    values = {}
    support_params = ['id', 'desc', 'name', 'is_public',
                      'tenant_name', 'status']
    for params in support_params:
        if params in search_opts:
            if params == 'tenant_name':
                values['owner_name'] = search_opts[params]
            elif params == 'desc':
                values['properties/description'] = search_opts[params]
            else:
                values[params] = search_opts[params]
    return filter_items(req, images, keys, 'owner', values)


def filter_security_groups(req, groups):
    '''
    groups sample as:
    [
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
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify security group owner
                tenantname, specify security group owner name
                name, specify security group name
                desc, specify security group description
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['tenant_name', 'name', 'description']
    values = {}
    support_params = ['desc', 'name', 'tenant_name']
    for params in support_params:
        if params in search_opts:
            if params == 'desc':
                values['description'] = search_opts[params]
            else:
                values[params] = search_opts[params]
    return filter_items(req, groups, keys, 'tenant_id', values)


def filter_floating_ips(req, ips):
    '''
    ips sample as:
    [{
    "instance_name": "test",
    "ip": "10.120.240.225",
     "fixed_ip": "10.0.0.2",
    "instance_id":"82fbc5f8-e60f-440a-a9a6-a5ab32cd2f68",
    "project_id": "dc32392af0ae4a098fb7235760077fa6",
    "project_name": "admin",
    "type"    : "public",
    "id": 1,
    "pool": "nova"
    }]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify IP owner
                tenantname, specify IP owner name
                ip, specify IP value
                type, specify IP type, public or private
                pool, specify IP pool name
                instance_name, specify
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['ip', 'type', 'pool', 'project_name', 'instance_name']
    values = {}
    support_params = ['ip', 'type', 'pool', 'tenant_name', 'instance_name']
    for params in support_params:
        if params in search_opts:
            if params == 'tenant_name':
                values['project_name'] = search_opts[params]
            else:
                values[params] = search_opts[params]
    return filter_items(req, ips, keys, 'project_id', values)


def filter_keypairs(req, keypairs):
    '''
     [
        {
            "fingerprint": "bf:ae:ac:34:44:c9:a8:0e:f5:04:67:35:a5:28:4d:7c",
            "name": "test-demo",
            "public_key": "ssh-rsa AAAxx== Generated by Nova",
            "user_id": "e0ef2619442f472c86951f84b210062d",
            "user_name": "demo"
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                userid, specify keypair owner
                username, specify keypair owner name
                name, specify keypair name
                fingerprint, specify keypair fingerprint
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['name', 'fingerprint', 'user_name']
    support_params = ['name', 'fingerprint', 'user_name']
    values = utils.get_support_keys(search_opts, support_params)
    return filter_items(req, keypairs, keys, 'user_id', values,
                        item_owner_id_key='userid')


def filter_instance_error(req, error):
    '''
    [
        {
            "code": "500",
            "created": "2012-12-05T06:25:33Z",
            "message": "NoValidHost",
            "name": "test",
            "tenant_id": "xxxx",
            "uuid": "c06f051f-1af6-48ff-90fd-871556771e99"
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify error instance owner
                name, specify error instance name
                uuid, specify error instance uuid
                code, specify http error code, should be string
                created, specify created time
                message, specify error message
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['name', 'uuid', 'code', 'created', 'message']
    support_params = ['name', 'uuid', 'code', 'created', 'message']
    values = utils.get_support_keys(search_opts, support_params)
    return filter_items(req, error, keys, 'tenant_id', values)


def filter_snapshot_error(req, error):
    '''
    [
        {
            "created": "2012-12-05T06:43:19",
            "desc": "create snapshot failed.",
            "id": "33b960f8-1e42-4c55-b83b-96ac0b3c8b8e",
            "name": "test",
            "owner": "dc32392af0ae4a098fb7235760077fa6"
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                key, search all fields when relationship is 'or'
                tenantid, specify error snapshot owner
                name, specify error snapshot name
                id, specify error snapshot id
                created, specify created time
                desc, specify error message
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['name', 'id', 'created', 'desc']
    support_params = ['name', 'id', 'created', 'desc']
    values = utils.get_support_keys(search_opts, support_params)
    return filter_items(req, error, keys, 'owner', values)


def filter_tenants_usages(req, usages):
    '''
    [
        {
            "public_qos_used": 50,
            "private_qos_used": 100,
            "tenant_id": "dc32392af0ae4a098fb7235760077fa6"
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or',
                tenantid, specify error snapshot owner
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = []
    values = {}
    return filter_items(req, usages, keys, 'tenant_id', values)


def filter_host_usages(req, usages):
    '''
    [
        {
            "hostname": "host1",
            "availability_zone": "nova",
            "ecus_used": 10,
            "local_gb_used": 40,
            "memory_mb_used": 128,
            "private_ips_used": 1,
            "private_qos_used": 123
        }
    ]
    :param req: request object contain filter keys.
                relationship, 'and' 'or'
                key, search all usages that equal
                              when relationship is 'or'
                hostname, search hostname that matched
                az, search availability zones
    '''
    search_opts = {}
    search_opts.update(req.GET)
    keys = ['hostname', 'availability_zone']
    values = {}
    support_params = ['hostname', 'az']
    for params in support_params:
        if params in search_opts:
            if params == 'az':
                values['availability_zone'] = search_opts[params]
            else:
                values[params] = search_opts[params]
    return filter_items(req, usages, keys, None, values)


def filter_quotas(req, tenant_id, quotas):
    '''
    In and condition, if tenantid and default specify,
    return value when tenant id in quotas or default value when tenant id
    not exists in quotas.
    In or condition, ignore default.
    {
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
    :param req: request object contain filter keys.
                relationship, 'and' 'or'
                key, search all usages that equal
                              when relationship is 'or'
                tenantid, search tenant that matched
                tenantname, search for tenant name
                default, when search in 'and' condition and specify
                                 tenant id and no result found, return default
                instances_use,
                instances_limit,
                security_groups_use,
                security_groups_limit,
                key_pairs_use,
                key_pairs_limit,
                cores_use,
                cores_limit,
                ecus_use,
                ecus_limit,
                ram_use,
                ram_limit,
                gigabytes_use,
                gigabytes_limit,
                private_floating_ips_use,
                private_floating_ips_limit,
                floating_ips_use,
                floating_ips_limit,
                private_network_bandwidth_use,
                private_network_bandwidth_limit,
                public_network_bandwidth_use,
                public_network_bandwidth_limit,
    :param tenant_id: id of tenant who request
    '''
    search_opts = {}
    search_opts.update(req.GET)
    result = []
    keys = ['instances_use', 'instances_limit',
            'security_groups_use', 'security_groups_limit',
            'key_pairs_use', 'key_pairs_limit',
            'cores_use', 'cores_limit',
            'ecus_use', 'ecus_limit',
            'ram_use', 'ram_limit',
            'gigabytes_use', 'gigabytes_limit',
            'private_floating_ips_use', 'private_floating_ips_limit',
            'floating_ips_use', 'floating_ips_limit',
            'private_network_bandwidth_use', 'private_network_bandwidth_limit',
            'public_network_bandwidth_use', 'public_network_bandwidth_limit']
    relationship = search_opts.pop('relationship', None)
    if relationship is None:
        return quotas
    need_default = search_opts.pop('default', False)
    need_default = need_default != False
    # Specify search for quota of tenantid
    tenantid = search_opts.pop('tenantid', None)
    tenant_name = search_opts.pop('tenantname', None)
    if relationship == 'or':
        _or_quotas_filter(quotas, result, search_opts, tenantid, keys,
                          need_default=need_default, tenant_name=tenant_name)
    elif relationship == 'and':
        _and_quotas_filter(quotas, result, search_opts, tenantid, keys,
                           need_default=need_default, tenant_name=tenant_name)
    else:
        raise exception.InvalidFilterItem(_("Relationship doesn't "
                                       "support any key except 'and', 'or'."))
    # If specify search for tenantid and no results return
    # and need return default quota, get default.
    if tenantid is not None and need_default and len(result) == 0\
            and relationship != 'or':
        LOG.debug(_("show default for tenant %s") % tenantid)
        quota = {}
        auth_token = req.headers.get('x-auth-token', None)
        if auth_token is None:
            LOG.warn(_('auth token not specified.'))
            return result
        default_quotas = ops_api.get_detault_quotas(tenant_id, tenantid,
                                                    auth_token)
        default_quotas = default_quotas.get('quota_set', {})
        for quota_set in default_quotas:
            if quota_set == 'id':
                continue
            item = {quota_set: {
                                'limit': default_quotas[quota_set],
                                'in_use': 0,
                                'reserved': 0
                                }}
            quota.update(item)
        quota.update(tenant_id=tenantid)
        result.append(quota)
    return result


def _and_quotas_filter(quotas, result, search_opts, tenantid, keys,
                       need_default=False, tenant_name=None):
    for quota in quotas:
        owner = quota.get('tenant_id', None)
        if owner is None:
            continue
        if tenantid != None and tenantid not in owner:
            continue
        if tenantid != None and tenantid in owner and need_default:
            # If tenant id satisfied and need default, ignore other filter.
            result.append(quota)
            return
        owner_name = quota.get('tenant_name', None)
        if tenant_name is not None and (owner_name is None or
                                        tenant_name not in owner_name):
            continue
        matched = True
        for key in keys:
            target = search_opts.pop(key, None)
            if target is None:
                # no search for this key
                continue
            try:
                target = int(target)
            except ValueError:
                LOG.debug(_("filter key is not int value key=%s")
                                                % target)
                continue
            # if searched but not match, should remove it.
            if key.endswith('_use'):
                key = key.replace('_use', '')
                item = quota.get(key, None)
                if item is None:
                    continue
                in_use = item.get('in_use', None)
                if in_use is None:
                    continue
                if target != in_use:
                    matched = False
                    break
            elif key.endswith('_limit'):
                key = key.replace('_limit', '')
                item = quota.get(key, None)
                if item is None:
                    continue
                limit = item.get('limit', None)
                if limit is None:
                    continue
                if target != limit:
                    matched = False
                    break
        if matched:
            result.append(quota)


def _or_quotas_filter(quotas, result, search_opts, tenantid, keys,
                      need_default=False, tenant_name=None):
    target = search_opts.pop('key', None)
    if target is None and tenantid is None:
        # If no search specified, return all.
        return quotas
    # At least specify one of tenant id or key to search
    # filter each quota to match for search opts.
    for quota in quotas:
        owner = quota.get('tenant_id', None)
        if owner is None:
            continue
        if tenantid != None and tenantid in owner:
            result.append(quota)
            continue
        owner_name = quota.get('tenant_name', None)
        if tenant_name is not None and (owner_name is not None and
                                        tenant_name in owner_name):
            result.append(quota)
            continue
        # If user does not specify tenant id to search
        # or tenant id not matched, search for key
        if target is None:
            continue
        try:
            target = int(target)
        except ValueError:
            LOG.debug(_("filter key is not int value key=%s")
                                            % target)
            continue
        # for each quota to compare all items use and limit
        for key in keys:
            if key.endswith('_use'):
                key = key.replace('_use', '')
                item = quota.get(key, None)
                if item is None:
                    continue
                in_use = item.get('in_use', None)
                if in_use is None:
                    LOG.debug(_("item %s has not key in_use") % item)
                    continue
                if target == in_use:
                    result.append(quota)
                    break
            elif key.endswith('_limit'):
                key = key.replace('_limit', '')
                item = quota.get(key, None)
                if item is None:
                    continue
                limit = item.get('limit', None)
                if limit is None:
                    LOG.debug(_("item %s has not key limit") % item)
                    continue
                if target == limit:
                    result.append(quota)
                    break
