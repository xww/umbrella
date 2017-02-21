import gettext
import stubout
import unittest

import umbrella.openstack.api

gettext.install('umbrella', unicode=1)


def fake_get_all_tenants(auth_token=None):
    return {
            "tenants": [
                {
                    "description": None,
                    "enabled": True,
                    "id": "04b8ef2f54a043739d770098a4a9bc37",
                    "name": "netease"
                },
                {
                    "description": "loadbalancerTenant",
                    "enabled": True,
                    "id": "0613e25153c94881bdd3287950191cf1",
                    "name": "loadbalancerTenant"
                },
                {
                    "description": "AuthorizationTest-tenant-desc",
                    "enabled": "true",
                    "id": "3fbde8c6c6ae431c9798c49d796cc066",
                    "name": "AuthorizationTest-tenant"
                },
                {
                    "description": "Project for pfadmin3",
                    "enabled": True,
                    "id": "0df3a3f5e6124d8c8abb7b42f4a70fe2",
                    "name": "Project_pfadmin3"
                },
            ],
            "tenants_links": []
        }


def fake_get_all_users(auth_token=None):
    return {
            "users": [
                {
                    "email": None,
                    "enabled": True,
                    "id": "15c24c1e696a4171b4d2eafdccfe9437",
                    "name": "neadmin",
                    "tenantId": None
                },
                {
                    "email": None,
                    "enabled": True,
                    "id": "1ae03a42d2364fb3bc9fa2162632fdc7",
                    "name": "demo",
                    "tenantId": "3fbde8c6c6ae431c9798c49d796cc066",
                    "tenantName": "AuthorizationTest-tenant"
                },
                {
                    "email": "lb@1243.com",
                    "enabled": True,
                    "id": "2640f31a0e2f42f58cd686187770b39d",
                    "name": "lb",
                    "tenantId": "0613e25153c94881bdd3287950191cf1",
                    "tenantName": "loadbalancerTenant"
                },
                {
                    "email": "hzfengchj@corp.netease.com",
                    "enabled": True,
                    "id": "302c8f85e2eb4794b242571259926eea",
                    "name": "pfadmin3",
                    "tenantId": "0df3a3f5e6124d8c8abb7b42f4a70fe2",
                    "tenantName": "Project_pfadmin3"
                }
            ]
        }


class BaseTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.stubs = stubout.StubOutForTesting()
        self.stubs.Set(umbrella.openstack.api, "get_all_tenants",
                       fake_get_all_tenants)
        self.stubs.Set(umbrella.openstack.api, "get_all_users",
                       fake_get_all_users)
