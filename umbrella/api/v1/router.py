# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from umbrella.api.v1 import api
from umbrella.common import wsgi


class API(wsgi.Router):

    """WSGI router for Glance v1 API requests."""

    def __init__(self, mapper):

        api_resource = api.create_resource()

        mapper.connect("/",
                       controller=api_resource,
                       action="index")
        mapper.connect("/images",
                       controller=api_resource,
                       action='index',
                       conditions={'method': ['GET']})
        mapper.connect("/images/{id}",
                       controller=api_resource,
                       action="show",
                       conditions=dict(method=["GET"]))
        mapper.connect("/net/{instance_uuid}",
                       controller=api_resource,
                       action="get_net_sample",
                       conditions=dict(method=["GET"]))
        mapper.connect("/cpu/{instance_uuid}",
                       controller=api_resource,
                       action="get_cpu_sample",
                       conditions=dict(method=["GET"]))
        mapper.connect("/disk/{instance_uuid}",
                       controller=api_resource,
                       action="get_disk_sample",
                       conditions=dict(method=["GET"]))
        mapper.connect("/mem/{instance_uuid}",
                       controller=api_resource,
                       action="get_mem_sample",
                       conditions=dict(method=["GET"]))



        super(API, self).__init__(mapper)
