'''
Created on 2012-11-2

@author: hzzhoushaoyu
'''
import time
from webob import exc

from umbrella.common import cfg
from umbrella.common import exception
from umbrella.common import local
from umbrella.common import timeutils
import umbrella.common.log as logging
from umbrella.openstack import client

CONF = cfg.CONF
admin_opts = [
              cfg.StrOpt("admin_user", default="admin"),
              cfg.StrOpt("admin_password", default="admin"),
              cfg.StrOpt("admin_tenant_name", default="admin")
              ]
cache_timeout_opts = [
                      cfg.IntOpt("user_cache_timeout", default=60 * 60 * 24),
                      cfg.IntOpt("flavor_cache_timeout", default=60 * 60),
                      cfg.IntOpt("image_cache_timeout", default=60 * 60 * 24),
                      cfg.IntOpt("quota_default_cache_timeout",
                                 default=60 * 60 * 24)
                      ]
CONF.register_opts(admin_opts)
CONF.register_opts(cache_timeout_opts)

LOG = logging.getLogger(__name__)


def normal_token(auth_token):
    if isinstance(auth_token, dict):
        return auth_token['id']
    elif isinstance(auth_token, str):
        return auth_token
    return None


def standardize_tenant_name(tenant):
    '''
    Add Project_ as prefix in tenant name except tenant name is empty.
    :param tenant: a dict looks like {
                                    'id': 'xxx',
                                    'name': 'xxx',
                                    }
    '''
    # FIXME(hzzhoushaoyu): As keystone has some tenants which are not created
    # from manage platform. These tenants' names have no Project_ prefix.
    # So add here manually to adjust sort method.
    tenant_name = tenant.get('name')
    prefix = 'Project_'
    if not tenant_name:
        return tenant
    if isinstance(tenant_name, unicode):
        tenant_name = str(tenant_name)
    if not isinstance(tenant_name, str):
        return tenant
    if tenant_name.startswith(prefix):
        return tenant
    tenant.update(name=(prefix + tenant_name))
    return tenant


def get_all_tenants(auth_token=None):
    cache = local.dict_store()
    auth_token = auth_token or request_admin_token()
    auth_token = normal_token(auth_token)
    c = client.KeystoneAdminClient()
    result, headers = c.response("GET", "/tenants",
                                 params={},
                                 headers={"x-auth-token": auth_token})
    for tenant in result['tenants']:
        tenant_id = tenant['id']
        standardize_tenant_name(tenant)
        cache.save_item('tenant', tenant_id, tenant,
                        timeout=CONF.user_cache_timeout)
    return result


def get_all_users(auth_token=None):
    cache = local.dict_store()
    auth_token = auth_token or request_admin_token()
    auth_token = normal_token(auth_token)
    c = client.KeystoneAdminClient()
    result, headers = c.response("GET", "/users",
                                 params={},
                                 headers={"x-auth-token": auth_token})
    for user in result['users']:
        user_id = user['id']
        tenant_id = user['tenantId']
        try:
            tenant = get_tenant(tenant_id, auth_token)
            user.update(tenantName=tenant['name'])
        except exc.HTTPNotFound:
            LOG.warn("user %s has no tenant associated." % user_id)
            pass
        cache.save_item('user', user_id, user,
                        timeout=CONF.user_cache_timeout)
    return result


def get_tenant(tenant_id, auth_token):
    '''
    return sample as:
    {'id': '4142dc247de848c58364d958a208d516',
    'enabled': True,
    'description': None,
    'name': 'demo'}
    '''
    cache = local.dict_store()
    tenant = cache.get_item('tenant', tenant_id)
    if tenant is not None:
        return tenant
    c = client.KeystoneAdminClient()
    try:
        result, headers = c.response("GET", "/tenants/%s" % tenant_id,
               params={},
               headers={"x-auth-token": auth_token})
    except exc.HTTPNotFound:
        result = {'tenant': {'id': '',
                            'enabled': False,
                            'description': None,
                            'name': ''}}
    try:
        result = result['tenant']
        standardize_tenant_name(result)
    except KeyError:
        raise exc.HTTPFailedDependency(_("Keystone method deprecated."))
    cache.save_item('tenant', tenant_id, result,
                    timeout=CONF.user_cache_timeout)
    return result


def get_user(user_id, auth_token):
    '''
    return sample as:
    {'email': 'z@1.com',
    'tenantName':'openstackDemo',
    'name': 'zsy',
    'enabled': True,
    'id': '771ac76cb3464a6580cdfe3d59351f37',
    'tenantId': 'f5d0a72747f34b2591aa9be636f15668'}
    '''
    cache = local.dict_store()
    user = cache.get_item('user', user_id)
    if user is not None:
        return user
    c = client.KeystoneAdminClient()
    try:
        result, headers = c.response("GET", "/users/%s" % user_id,
               params={},
               headers={"x-auth-token": auth_token})
    except exc.HTTPNotFound:
        result = {'user': {'email': '',
                            'tenantName': '',
                            'name': '',
                            'enabled': False,
                            'id': '',
                            'tenantId': ''}}
    try:
        result = result['user']
    except KeyError:
        raise exc.HTTPFailedDependency(_("Keystone method deprecated."))
    tenant_id = result['tenantId']
    try:
        tenant = get_tenant(tenant_id, auth_token)
        result.update(tenantName=tenant['name'])
    except exc.HTTPNotFound:
        LOG.warn("user %s has no tenant associated." % user_id)
        pass
    cache.save_item('user', user_id, result,
                    timeout=CONF.user_cache_timeout)
    return result


def get_flavor(tenant_id, auth_token, flavor_id):
    cache = local.dict_store()
    flavor = cache.get_item('flavor', flavor_id)
    if flavor is not None:
        return flavor
    c = client.NovaClient()
    try:
        result, headers = c.response("GET",
                                 "/%s/flavors/%s" % (tenant_id, flavor_id),
                                 params={},
                                 headers={"x-auth-token": auth_token})
    except exc.HTTPNotFound:
        return None

    result = get_extra_specs(c, result, tenant_id, auth_token, flavor_id)
    if result is not None:
        cache.save_item('flavor', flavor_id, result,
                    timeout=CONF.flavor_cache_timeout)
    return result


def get_extra_specs(c, result, tenant_id, auth_token, flavor_id):
    try:
        extra_specs, headers = c.response("GET",
                "/%s/flavors/%s/os-extra_specs" % (tenant_id, flavor_id),
                params={},
                headers={"x-auth-token": auth_token})
    except exc.HTTPNotFound:
        result['flavor']['nbs'] = 'false'
        return result
    result['flavor']['nbs'] = extra_specs['extra_specs'].get('nbs', 'false')
    return result


def list_flavor(tenant_id, auth_token, detailed=False):
    c = client.NovaClient()
    path = "/%s/flavors" % tenant_id
    if detailed:
        path += "/detail"
    result, headers = c.response("GET",
                                 path,
                                 params={},
                                 headers={"x-auth-token": auth_token})
    return result


def get_image(auth_token, image_id):
    cache = local.dict_store()
    image = cache.get_item('image', image_id)
    if image is not None:
        return image
    c = client.GlanceClient()
    try:
        result, headers = c.response("HEAD",
                                 "/images/%s" % image_id,
                                 params={},
                                 headers={"x-auth-token": auth_token})
    except exc.HTTPNotFound:
        return None
    image = {}
    for k, v in headers:
        if k.lower().startswith("x-image-meta"):
            k = k.lower().replace("x-image-meta", 'image')
            image.update({k: v})
    image_owner = image.get('image-owner')
    if image_owner is not None:
        tenant = get_tenant(image_owner, auth_token)
        tenant_name = tenant['name']
        image.update({'image-owner-name': tenant_name})
    cache.save_item('image', image_id, image,
                    timeout=CONF.image_cache_timeout)
    return image


def get_keypairs(tenant_id, auth_token):
    '''
    return all key pairs list
    '''
    # should not cache for key pairs
    c = client.NovaClient()
    result, headers = c.response("GET",
                    "/%s/os-keypairs-search" % tenant_id,
                    params={"all_tenants": 1},
                    headers={"x-auth-token": auth_token})
    return result['keypairs']


def get_detault_quotas(tenant_id, target_id, auth_token):
    cache = local.dict_store()
    # Note(hzzhoushaoyu): Save for who request quota default(tenant_id),
    # not whose quota default(target_id).
    quota_default = cache.get_item('quota_default', tenant_id)
    if quota_default is not None:
        return quota_default
    c = client.NovaClient()
    result, headers = c.response("GET",
                    "/%s/os-quota-sets/%s/defaults" % (tenant_id, target_id),
                    params={},
                    headers={"x-auth-token": auth_token})
    cache.save_item('quota_default', tenant_id, result,
                    timeout=CONF.quota_default_cache_timeout)
    return result


def get_hosts_capacity(tenant_id, auth_token):
    '''
    return dict contained resource capacity of all hosts.
    samples as {"114-113-199-11": {"ecus": 1, "disk_gb": 1, "memory_mb": 1,
                "public_network_qos_mbps": 1, "private_network_qos_mbps": 1}}
    '''
    c = client.NovaClient()
    try:
        result, headers = c.response("GET",
                                 "/%s/os-quotas-usage/hosts" % tenant_id,
                                 params={},
                                 headers={"x-auth-token": auth_token})
    except exc.HTTPUnauthorized:
        raise exception.NotAuthenticated(_("Auth Failed for getting "
                                           "quotas usage."))
    return result


def get_hosts_az(tenant_id, auth_token):
    '''
    return dict contained available zones and their hosts.
    samples as {'availability_zones':
                    [
                     {
                      'zoneState': 'available',
                      'hosts': ['host3'],
                      'zoneName': 'nova1'
                      },
                     {
                      'zoneState': 'available',
                      'hosts': ['host1', 'host2'],
                      'zoneName': 'nova'
                      }
                     ]
                    }
    '''
    c = client.NovaClient()
    try:
        result, headers = c.response("GET",
                                 "/%s/availability-zones" % tenant_id,
                                 params={},
                                 headers={"x-auth-token": auth_token})
    except exc.HTTPUnauthorized:
        raise exception.NotAuthenticated(_("Auth Failed for getting "
                                           "quotas usage."))
    return result


def get_usages(tenant_id, auth_token):
    '''
    return dict contained all usages.
    samples as {"ecus":[], "floating_ips":[]}
    '''
    LOG.debug(_("getting usage from NOVA."))
    c = client.NovaClient()
    try:
        result, headers = c.response("GET",
                                 "/%s/os-quotas-usage" % tenant_id,
                                 params={},
                                 headers={"x-auth-token": auth_token})
    except exc.HTTPUnauthorized:
        raise exception.NotAuthenticated(_("Auth Failed for getting "
                                           "quotas usage."))
    _convert_floating_ips(result)
    _convert_network_qos(result)
    _convert_servers(result)
    return result


def _convert_servers(result):
    for server in result['servers']['servers']:
        server.update(used=1)


def _convert_floating_ips(result):
    # private floating IPs
    pri_ips = []
    # public floating IPs
    pub_ips = []
    for ip in result['floating_ips']:
        if ip['project_id'] is not None:
            ip.update({'used': 1})
        else:
            ip.update({'used': 0})
        if ip['type'] == 'public':
            pub_ips.append(ip)
        elif ip['type'] == 'private':
            pri_ips.append(ip)
    private_ip_usage = {
                        "private_ips": pri_ips,
                        "capacity": len(pri_ips)
                        }
    public_ip_usage = {
                        "public_ips": pub_ips,
                        "capacity": len(pub_ips)
                        }
    del result['floating_ips']
    result.update({
            "private_ips": private_ip_usage,
            "public_ips": public_ip_usage
            })


def _convert_network_qos(result):
    # private QoS
    pri_qos = []
    # public QoS
    pub_qos = []
    for qos in result['network_qos']['network_qos']:
        if qos['type'] == 'public':
            pub_qos.append(qos)
        elif qos['type'] == 'private':
            pri_qos.append(qos)
    private_qos_usage = {
                        "private_qos": pri_qos,
                        "capacity": result['network_qos']['private_capacity']
                        }
    public_qos_usage = {
                        "public_qos": pub_qos,
                        "capacity": result['network_qos']['public_capacity']
                        }
    del result['network_qos']
    result.update({
            "private_qos": private_qos_usage,
            "public_qos": public_qos_usage
            })


def request_admin_token(search_cache=True):
    """Retrieve new token as admin user from keystone.

    :return token id upon success
    :raises ServerError when unable to communicate with keystone

    """
    admin_user = CONF.get('admin_user')
    admin_password = CONF.get('admin_password')
    admin_tenant_name = CONF.get('admin_tenant_name')
    keystone_client = client.KeystonePublicClient()
    local_store = local.dict_store()
    if search_cache and hasattr(local_store, 'admin_token'):
        token = local_store.admin_token
        expires = timeutils.parse_isotime(token['expires'])
        if not timeutils.is_older_than(timeutils.normalize_time(expires),
                                        0):
            LOG.debug(_("Get token from local store."))
            return token
    params = {
        'auth': {
            'passwordCredentials': {
                'username': admin_user,
                'password': admin_password,
            },
            'tenantName': admin_tenant_name,
        }
    }

    data, headers = keystone_client.response('POST',
                            '/tokens',
                            headers={"content-type": "application/json"},
                            body=params)

    try:
        token = data['access']['token']
        assert token
        local_store.admin_token = token
        LOG.debug(_("Request for admin token and save to local store."))
        return token
    except (AssertionError, KeyError):
        LOG.warn("Unexpected response from keystone service: %s", data)
        raise


def init():
    # Cache all tenants and all users when server start up.
    # 'init_methods' configured in common.wsgi
    retry = True
    while retry:
        try:
            get_all_tenants()
            get_all_users()
            retry = False
        except exception.ClientConnectionError:
            retry = True
            LOG.warn("Getting tenant and user info failed because of keystone"
                     " Connecting error, retry again!")
            time.sleep(3)
