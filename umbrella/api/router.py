'''
Created on 2012-10-21

@author: hzzhoushaoyu
'''

from umbrella.common import wsgi
from umbrella.api import user
from umbrella.api import server
from umbrella.api import image
from umbrella.api import statistic
from umbrella.api import monitor


class API(wsgi.Router):

    """WSGI router for Umbrella API requests."""

    def __init__(self, mapper):
        self._user_api(mapper)
        self._server_api(mapper)
        self._image_api(mapper)
        self._statistic_api(mapper)

        super(API, self).__init__(mapper)

    def _user_api(self, mapper):
        user_resource = user.create_resource()

        mapper.connect("/users",
                       controller=user_resource, action="index",
                       conditions=dict(method=["GET"]))
        mapper.connect("/tenants",
                       controller=user_resource, action="index",
                       conditions=dict(method=["GET"]))
        mapper.connect("/users/{id}",
                       controller=user_resource, action="show",
                       conditions=dict(method=["GET"]))

        mapper.connect("/tenants/{id}",
                       controller=user_resource, action="show",
                       conditions=dict(method=["GET"]))

        #set user password api
        mapper.connect("/users/{user_id}/OS-KSADM/password",
                       controller=user_resource, action="set_password",
                       conditions=dict(method=["PUT"]))

        #user enable api
        mapper.connect("/users/{user_id}",
                       controller=user_resource, action="update_user",
                       conditions=dict(method=["PUT"]))
        mapper.connect("/users/{id}",
                       controller=user_resource, action="delete_user",
                       conditions=dict(method=["DELETE"]))
        mapper.connect("/tenants/{id}",
                       controller=user_resource, action="delete_user",
                       conditions=dict(method=["DELETE"]))

    def _server_api(self, mapper):
        server_resource = server.create_resource()

        #tenant usage api
        mapper.connect("/{tenant_id}/os-simple-tenant-usage",
                       controller=server_resource, action="get_usage",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/os-simple-tenant-usage/{target_id}",
                       controller=server_resource, action="get_usage",
                       conditions=dict(method=["GET"]))
        mapper.connect(
                    "/{tenant_id}/os-simple-tenant-usage/{host}/show_by_host",
                    controller=server_resource, action="get_host_usage",
                    conditions=dict(method=["GET"]))

        #tenant quota sets api
        mapper.connect("/{tenant_id}/os-quota-sets/{target_id}",
                       controller=server_resource, action="list_quotas",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/os-quota-sets/{target_id}",
                       controller=server_resource, action="update_quotas",
                       conditions=dict(method=["PUT"]))
        mapper.connect("/{tenant_id}/os-quota-sets",
                       controller=server_resource,
                       action="list_all_quotas",
                       conditions=dict(method=["GET"]))

        #api for keypairs of all tenants
        mapper.connect("/{tenant_id}/os-keypairs-search",
                       controller=server_resource, action="list_keypairs",
                       conditions=dict(method=["GET"]))

        #server info API
        mapper.connect("/{tenant_id}/servers/detail",
                       controller=server_resource, action="index",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/servers/{id}",
                       controller=server_resource, action="show",
                       conditions=dict(method=["GET"]))
        #delete server API
        mapper.connect("/{tenant_id}/servers/{id}",
                       controller=server_resource, action="delete",
                       conditions=dict(method=["DELETE"]))

        #az info API
        mapper.connect("/{tenant_id}/availability-zones",
                       controller=server_resource, action="list_az",
                       conditions=dict(method=["GET"]))

        #flavor info API
        # Note: Make sure these URL mapper before
        # "/{tenant_id}/flavors/{flavor_id}".
        # since the `key_info` can be parsed into
        # {flavor_id} to make strange things.
        mapper.connect("/{tenant_id}/flavors/key_id",
                       controller=server_resource, action="list_flavor_key_id",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/flavors/key_info",
                     controller=server_resource, action="list_flavor_key_info",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/flavors/{flavor_id}",
                       controller=server_resource, action="get_flavor",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/flavors/detail",
                       controller=server_resource, action="get_flavor",
                       conditions=dict(method=["GET"]))
        #create flavor API
        mapper.connect("/{tenant_id}/flavors",
                       controller=server_resource, action="create_flavor",
                       conditions=dict(method=["POST"]))
        #delete flavor API
        mapper.connect("/{tenant_id}/flavors/{flavor_id}",
                       controller=server_resource, action="delete_flavor",
                       conditions=dict(method=["DELETE"]))

        #server action API include pause, suspend, reboot, console, vnc
        mapper.connect("/{tenant_id}/servers/{server_id}/action",
                       controller=server_resource, action="server_action",
                       conditions=dict(method=["POST"]))

        #API for listing floating IPs of all tenants
        mapper.connect("/{tenant_id}/os-floating-ips-search",
                       controller=server_resource, action="list_floating_ips",
                       conditions=dict(method=["GET"]))

        #API for listing security groups and rules
        mapper.connect("/{tenant_id}/os-security-groups",
                       controller=server_resource,
                       action="list_security_groups",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/os-security-groups/{id}",
                       controller=server_resource,
                       action="show_security_group",
                       conditions=dict(method=["GET"]))

        mapper.connect(
                    "/{tenant_id}/servers/{server_id}/network-qos/{qos_type}",
                    controller=server_resource,
                    action="modify_network_qos",
                    conditions=dict(method=["PUT"]))

    def _image_api(self, mapper):
        image_resource = image.create_resource()

        mapper.connect("/images/detail",
                       controller=image_resource, action="index",
                       conditions=dict(method=["GET"]))
        mapper.connect("/images/{image_id}",
                       controller=image_resource, action="show",
                       conditions=dict(method=["HEAD"]))
        mapper.connect("/images/{image_id}",
                       controller=image_resource, action="delete",
                       conditions=dict(method=["DELETE"]))
        mapper.connect("/images/{image_id}",
                       controller=image_resource, action="update",
                       conditions=dict(method=["PUT"]))

    def _statistic_api(self, mapper):
        statistic_resource = statistic.create_resource()

        mapper.connect("/{tenant_id}/statistics",
                       controller=statistic_resource, action="index",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/statistics/platform",
                       controller=statistic_resource,
                       action="list_platform_usage",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/statistics/az/{az_name}",
                       controller=statistic_resource,
                       action="list_az_usage",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/statistics/tenant",
                       controller=statistic_resource, action="show_by_tenant",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/statistics/host",
                       controller=statistic_resource, action="show_by_host",
                       conditions=dict(method=["GET"]))

        mapper.connect("/{tenant_id}/statistics/instance/success",
                       controller=statistic_resource,
                       action="statistic_instance_success",
                       conditions=dict(method=["GET"]))
        mapper.connect("/{tenant_id}/statistics/instance/error",
                       controller=statistic_resource,
                       action="statistic_instance_error",
                       conditions=dict(method=["GET"]))

        mapper.connect("/statistics/snapshot/success",
                       controller=statistic_resource,
                       action="statistic_snapshot_create_success",
                       conditions=dict(method=["GET"]))
        mapper.connect("/statistics/snapshot/error",
                       controller=statistic_resource,
                       action="statistic_snapshot_create_error",
                       conditions=dict(method=["GET"]))


class MonitorAPI(wsgi.Router):

    """WSGI router for monitor API requests."""

    def __init__(self, mapper):
        monitor_resource = monitor.create_resource()

        mapper.connect("/settings/{level}/{setting_type}",
                       controller=monitor_resource,
                       action="get_setting_by_level_type",
                       conditions=dict(method=["GET"]))
        mapper.connect("/settings/{uuid}",
                       controller=monitor_resource,
                       action="get_setting_by_uuid",
                       conditions=dict(method=["GET"]))
        mapper.connect("/settings",
                       controller=monitor_resource, action="list_settings",
                       conditions=dict(method=["GET"]))
        mapper.connect("/settings",
                       controller=monitor_resource, action="save_setting",
                       conditions=dict(method=["POST"]))
        mapper.connect("/settings/{uuid}",
                       controller=monitor_resource, action="save_setting",
                       conditions=dict(method=["PUT"]))
        mapper.connect("/settings/{uuid}",
                       controller=monitor_resource, action="destroy_setting",
                       conditions=dict(method=["DELETE"]))

        mapper.connect("/alarms", controller=monitor_resource,
                       action="list_alarms",
                       conditions=dict(method=["GET"]))
        mapper.connect("/alarms/{alarm_id}", controller=monitor_resource,
                       action="get_alarm",
                       conditions=dict(method=["GET"]))
        mapper.connect("/alarms/{alarm_id}", controller=monitor_resource,
                       action="update_alarm",
                       conditions=dict(method=["PUT"]))
        mapper.connect("/alarms", controller=monitor_resource,
                       action="clear_alarms",
                       conditions=dict(method=["DELETE"]))
        mapper.connect("/alarms/{alarm_id}", controller=monitor_resource,
                       action="delete_alarm",
                       conditions=dict(method=["DELETE"]))

        super(MonitorAPI, self).__init__(mapper)
