'''
Created on 2012-10-24

@author: hzzhoushaoyu
'''
import netaddr
from webob import exc

from umbrella.common import cfg
from umbrella.common import utils
from umbrella.api.list_operation import filter as list_filter
from umbrella.api.list_operation import sort as list_sort
from umbrella.common import wsgi
from umbrella.openstack import client
from umbrella.openstack import api as ops_api
import umbrella.common.log as logging
from umbrella.common import timeutils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

NOSTATE = 0x00
RUNNING = 0x01
PAUSED = 0x03
SHUTDOWN = 0x04  # the VM is powered off
CRASHED = 0x06
SUSPENDED = 0x07
BUILDING = 0x09

_STATE_MAP = {
    NOSTATE: 'pending',
    RUNNING: 'running',
    PAUSED: 'paused',
    SHUTDOWN: 'shutdown',
    CRASHED: 'crashed',
    SUSPENDED: 'suspended',
    BUILDING: 'building',
}

opts = [
        cfg.ListOpt("private_floating_ip_range", default=["10.120.31.0/24", ]),
        cfg.ListOpt("floating_range", default=["10.120.240.224/27", ])
        ]
CONF.register_opts(opts)


def _recog_ip_type(ip):
    '''
    :retval : is_floating_ip, ip type
    '''
    # Note(hzrandd):Support for multiple ip segment
    private_ip_range = CONF.private_floating_ip_range
    private_network = []
    for private in private_ip_range:
        private_network.append(netaddr.IPNetwork(private))

    public_ip_range = CONF.floating_range
    public_network = []
    for public in public_ip_range:
        public_network.append(netaddr.IPNetwork(public))

    ip = netaddr.IPAddress(ip)

    for private_ip in private_network:
        if ip in private_ip:
            return True, 'private'

    for public_ip in public_network:
        if ip in public_ip:
            return True, 'public'

    return False, 'fixed'


def _get_nbs_info(flavor):
    try:
        nbs = flavor['extra_specs'].get('nbs', 'false').lower()
    except (KeyError, AttributeError):
        nbs = 'false'
    return 0 if nbs == 'false' else 1


def _get_ecus_info(flavor):
    try:
        ecus = flavor['extra_specs'].get('ecus_per_vcpu:', '')
    except (KeyError, AttributeError):
        ecus = ''
    return int(ecus) if ecus else 0


def _is_flavor_for_creating(flavor):
    # Note:filter out the flavor which name is begin with 'flavor_',make sure
    # use these flavor to create instance.
    return 'flavor_' in flavor['name']


class Controller():

    def _get_power_state(self, power_state):
        return _STATE_MAP.get(power_state, "Unknown-State")

    def _repack_server_data(self, server, req, tenant_id):
        server.update({"OS-EXT-STS:power_state":
                      self._get_power_state(server['OS-EXT-STS:power_state'])})
        auth_token = req.headers.get("x-auth-token")
        # get flavor info
        flavor_id = server['flavor']['id']
        flavor = ops_api.get_flavor(tenant_id,
                           auth_token,
                           flavor_id)
        if flavor is not None:
            for k, v in flavor['flavor'].iteritems():
                if k == 'links':
                    continue
                server.update({"flavor-%s" % k: v})
            server.pop('flavor')

        server_owner_id = server['tenant_id']
        # get tenant name
        tenant = ops_api.get_tenant(server_owner_id, auth_token)
        tenant_name = tenant['name']
        server.update(tenant_name=tenant_name)

        fixed_ips = []
        private_floating_ips = []
        public_floating_ips = []
        # recognize IP type
        for ip in server['addresses'].get('private', {}):
            is_floating_ip, ip_type = _recog_ip_type(ip['addr'])
            if is_floating_ip and ip_type == 'private':
                private_floating_ips.append(ip)
            elif is_floating_ip and ip_type == 'public':
                public_floating_ips.append(ip)
            else:
                fixed_ips.append(ip)
        server.update(fixed_ips=fixed_ips)
        server.update(private_floating_ips=private_floating_ips)
        server.update(public_floating_ips=public_floating_ips)

        # get image info
        image_id = server['image']['id']
        image = ops_api.get_image(auth_token, image_id)
        if image is not None:
            server.update(image)
            server.pop('image')

        # get running time (now - created_at)
        # FIXME(hzzhoushaoyu): created_at should transform to utc+0 datetime,
        # but as list show required nova return utc+8 datetime.
        # If nova return utc+0 datetime, running time may be ERROR data.
        created_at = server['created']
        created_datetime = timeutils.normalize_time(
                timeutils.local_to_utc(
                    timeutils.parse_strtime(created_at, '%Y-%m-%d %H:%M:%S')))
        running_time = timeutils.seconds_from_now(created_datetime)
        server.update({"running_seconds": running_time})
        return server

    def _nova_request(self, req):
        c = client.NovaClient()
        result, headers = c.request(req)
        return result, headers

    def get_usage(self, req, tenant_id, target_id=None):
        '''
        get all tenants usage info if target_id is None
        if target_id is specified, return the target usage info
        '''
        result, headers = self._nova_request(req)
        return result

    def get_host_usage(self, req, tenant_id, host):
        '''
        get all tenants usage info if target_id is None
        if target_id is specified, return the target usage info
        '''
        result, headers = self._nova_request(req)
        return result

    @utils.convert_mem_from_mb_to_gb
    def list_quotas(self, req, tenant_id, target_id):
        '''
        get specify tenant quota sets for target_id
        '''
        result, headers = self._nova_request(req)
        return result

    def update_quotas(self, req, tenant_id, target_id, body):
        '''
        update user quotas
        '''
        result, headers = self._nova_request(req)
        return result

    @utils.log_func_exe_time
    @utils.convert_mem_from_mb_to_gb
    def list_all_quotas(self, req, tenant_id):
        '''
        get all quota sets
        '''
        # Request quota and usage
        result, headers = self._nova_request(req)
        converted_result = []
        auth_token = req.headers.get("x-auth-token")

        # Request keypair list and calculate usage
        keypairs = ops_api.get_keypairs(tenant_id, auth_token)
        for keypair in keypairs:
            userid = keypair['keypair'].get('user_id', None)
            if userid is None:
                continue
            tenant = ops_api.get_user(userid, auth_token)
            keypair_owner = tenant.get('tenantId', None)
            if keypair_owner is None:
                continue
            target_usage = result.get(keypair_owner, None)
            if target_usage is None:
                # no tenant in quota usage id for this keypair_owner
                continue
            target_keypair_usage = target_usage.get('key_pairs', {})
            target_keypair_in_use = target_keypair_usage.get('in_use', 0)
            in_use = int(target_keypair_in_use) + 1
            target_keypair_usage.update(in_use=in_use)
        # Insert tenant_id and tenant name in each item
        for tenantid in result:
            item = result[tenantid]
            item.update({"tenant_id": tenantid})
            tenant = ops_api.get_tenant(tenantid, auth_token)
            item.update(tenant_name=tenant['name'])
            converted_result.append(item)
        filter_result = list_filter.filter_quotas(req, tenant_id,
                                                  converted_result)
        sort_result = list_sort.sort_quotas(req, filter_result)
        sort_result = [re for re in sort_result if re.get('tenant_id', '')]
        return dict(quotas=sort_result)

    def list_keypairs(self, req, tenant_id):
        '''
        list key pairs
        support all_tenants=True
        '''
        result, headers = self._nova_request(req)
        auth_token = req.headers.get("x-auth-token")
        try:
            keypairs = result['keypairs']
            keypair_list_ret = []
            for item in keypairs:
                keypair = item['keypair']
                user = ops_api.get_user(keypair['user_id'], auth_token)
                keypair.update(user_name=user['name'])
                if 'tenantName' in user:
                    keypair.update(
                            tenant_name=user['tenantName'],
                            tenant_id=user['tenantId'])
                    fingerprint = keypair.get('fingerprint', '').\
                                            replace('.create', '')
                    keypair.update(fingerprint=fingerprint)
                keypair_list_ret.append(keypair)
            keypair_list_ret = list_filter.filter_keypairs(req,
                                                           keypair_list_ret)
            keypair_list_ret = list_sort.sort_keypairs(req, keypair_list_ret)
        except KeyError:
            LOG.exception(_("repack keypair data error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))
        return dict(keypairs=keypair_list_ret)

    @utils.log_func_exe_time
    def index(self, req, tenant_id):
        '''
        list servers api
        support all_tenants=True param to list servers of all tenants
        support attribute filters like name=test
        '''
        result, headers = self._nova_request(req)
        servers = []
        try:
            for server in result['servers']:
                server = self._repack_server_data(server, req, tenant_id)
                if "links" in server:
                    del server["links"]
                servers.append(server)
        except KeyError:
            LOG.exception(_("repack server data error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))
        servers = list_filter.filter_servers(req, servers)
        servers = list_sort.sort_servers(req, servers)
        return dict(servers=servers)

    def show(self, req, tenant_id, id):
        '''
        show server by server id
        '''
        result, headers = self._nova_request(req)
        try:
            server = self._repack_server_data(result['server'], req, tenant_id)
            if "links" in server:
                    del server["links"]
            return server
        except KeyError:
            LOG.exception(_("repack server data error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))

    def delete(self, req, tenant_id, id):
        '''
        delete server by server id
        '''
        result, headers = self._nova_request(req)
        return result

    def list_az(self, req, tenant_id):
        '''
        list availability-zones info
        '''
        auth_token = req.headers.get("x-auth-token")
        result = ops_api.get_hosts_az(tenant_id, auth_token)
        return result

    def get_flavor(self, req, tenant_id, flavor_id):
        '''
        get flavor info by flavor id
        '''
        result, headers = self._nova_request(req)
        return result

    def _get_map_flavor(self, req, tenant_id, flavor_id):
        c = client.NovaClient()

        def get_flavors(c, tenant_id):
            auth_token = req.headers.get("x-auth-token")
            result, headers = c.response("GET",
                            "/%s/flavors/detail?is_public=None" % (tenant_id),
                           params={},
                           headers={"x-auth-token": auth_token})
            return result

        return get_flavors(c, tenant_id)

    def list_flavor_key_info(self, req, tenant_id, flavor_id=None):
        result = self._get_map_flavor(req, tenant_id, flavor_id)

        def get_number(flavors):
            re = {}
            for p in flavors:
                nbs = _get_nbs_info(p)
                ecus = _get_ecus_info(p)
                if _is_flavor_for_creating(p):
                    info_str = "%d_%d_%d_%d_%d" % (
                                         p['vcpus'],
                                         ecus,
                                         p['ram'],
                                         p['OS-FLV-EXT-DATA:ephemeral'],
                                         nbs)
                    re[info_str] = int(p['id'])
            return re

        result = get_number(result['flavors'])
        return result

    def list_flavor_key_id(self, req, tenant_id, flavor_id=None):
        result = self._get_map_flavor(req, tenant_id, flavor_id)

        def get_map_id(flavors):
            re = {}
            for k in flavors:
                nbs = _get_nbs_info(k)
                ecus = _get_ecus_info(k)
                re[k['id']] = {
                               'vcpus': k['vcpus'],
                               'ecu': ecus,
                               'memory': k['ram'],
                               'ephemeral_gb': k['OS-FLV-EXT-DATA:ephemeral'],
                               'nbs': nbs}
            return re

        result = get_map_id(result['flavors'])
        return result

    def create_flavor(self, req, tenant_id, body):
        '''
        create flavor with flavor info in body
        '''
        result, headers = self._nova_request(req)
        return result

    def delete_flavor(self, req, tenant_id, flavor_id):
        '''
        create flavor with flavor info in body
        '''
        result, headers = self._nova_request(req)
        return result

    def server_action(self, req, tenant_id, server_id, body):
        '''
        server action described in body and server id in url
        '''
        result, headers = self._nova_request(req)
        return result

    @utils.log_func_exe_time
    def list_floating_ips(self, req, tenant_id):
        '''
        list all floating ip
        '''
        result, headers = self._nova_request(req)
        auth_token = req.context.auth_tok
        try:
            for floating_ip in result['floating_ips']:
                project_id = floating_ip['project_id']
                if project_id is not None:
                    tenant = ops_api.get_tenant(project_id, auth_token)
                    project_name = tenant['name']
                    floating_ip.update(project_name=project_name)
        except KeyError:
            LOG.exception(_("list floating ip error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))
        except exc.HTTPNotFound:
            LOG.error(_("project_id %s not found.") % project_id)
            raise exc.HTTPNotFound(_("project_id %s not found for"
                " floating ip %s.") % (project_id, floating_ip))
        pools = result.get('pools', None)
        ips = result.get('floating_ips', None)
        ips = list_filter.filter_floating_ips(req, ips)
        ips = list_sort.sort_floating_ips(req, ips)
        if pools is not None:
            return dict(pools=pools, floating_ips=ips)
        else:
            return dict(floating_ips=ips)

    @utils.log_func_exe_time
    def list_security_groups(self, req, tenant_id):
        '''
        list all security groups
        '''
        result, headers = self._nova_request(req)
        try:
            groups = result['security_groups']
            auth_token = req.context.auth_tok
            for group in groups:
                group.pop("rules")
                tenant_id = group.get("tenant_id")
                tenant = ops_api.get_tenant(tenant_id, auth_token)
                tenant_name = tenant['name']
                group.update(tenant_name=tenant_name)
            groups = list_filter.filter_security_groups(req, groups)
            groups = list_sort.sort_security_groups(req, groups)
            return dict(security_groups=groups)
        except KeyError:
            LOG.exception(_("repack server data error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))

    def modify_network_qos(self, req, tenant_id, server_id, qos_type, body):
        '''
        modify network qos of specify instance
        '''
        if qos_type == 'all':
            c = client.NovaClient()
            update_rates = body
            private_rate = update_rates.get('private_rate', None)
            public_rate = update_rates.get('public_rate', None)
            # NOTE(hzzhoushaoyu): Body from request may be not the same size
            # with the following requests.So Nova wait for more content until
            # timeout.
            req.headers.pop('Content-Length', None)
            if private_rate:
                path = req.path.replace('all', 'private')
                private_qos_body = dict(rate=private_rate)
                c.response('PUT', path, req.params.mixed(), req.headers,
                           private_qos_body)
            if public_rate:
                path = req.path.replace('all', 'public')
                public_qos_body = dict(rate=public_rate)
                c.response('PUT', path, req.params.mixed(), req.headers,
                           public_qos_body)
            result = None
        else:
            result, headers = self._nova_request(req)
        return result

    def show_security_group(self, req, tenant_id, id):
        '''
        show specified security group rules
        '''
        result, headers = self._nova_request(req)
        try:
            return result['security_group']
        except KeyError:
            LOG.exception(_("repack server data error."))
            raise exc.HTTPFailedDependency(_("Nova method deprecated."))


def create_resource():
    """Servers resource factory method"""
    return wsgi.Resource(Controller())
