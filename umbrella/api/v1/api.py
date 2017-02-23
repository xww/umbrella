# Copyright 2013 OpenStack Foundation
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

"""
"""


from oslo_config import cfg
from oslo_log import log as logging
from umbrella.common import wsgi
from umbrella import i18n
from umbrella.db.sqlalchemy import api as db_api
from umbrella.db.sqlalchemy import models
import time
import json

LOG = logging.getLogger(__name__)
_ = i18n._
_LE = i18n._LE
_LI = i18n._LI
_LW = i18n._LW

CONF = cfg.CONF


class Controller():
    """
    WSGI controller for api resource in Umbrella v1 API

    The resource API is a RESTful web service for image data. The API
    is as follows::

        GET /api/{net,cpu,disk,mem}/instance-uuid?from=time1&&to=time2
        -- Returns a set of
        resource data
    """
    
    def __init__(self):
        #self.notifier = notifier.Notifier()
        #registry.configure_registry_client()
        #self.policy = policy.Enforcer()
        #if property_utils.is_property_protection_enabled():
        #    self.prop_enforcer = property_utils.PropertyRules(self.policy)
        #else:
        #    self.prop_enforcer = None
        pass
    
    def get_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        DB_CONNECT_STRING = 'mysql://root:ubuntu@compute1/umbrella'
        engine = create_engine(DB_CONNECT_STRING, echo=True)
        DB_Session = sessionmaker(bind=engine)
        session = DB_Session()
        return session       
        

    def time_format(self,timeValue):
        timeStamp = int(time.mktime(time.strptime(timeValue,"%Y-%m-%dT%H-%M-%SZ")))
        timeArray = time.localtime(timeStamp)
        timeStr=time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
        return timeStr

    def time_format(self,timeValue):
        timeStamp = int(time.mktime(time.strptime(timeValue,"%Y-%m-%dT%H-%M-%SZ")))
        #print "time ========",timeStamp
        timeArray = time.localtime(timeStamp)
        timeStr=time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
        #print "timeStr ======",timeStr
        return timeStr

    def get_net_sample(self, req, instance_uuid):
        params = {}
        params.update(req.GET)
        start_time = self.time_format(params['start'])
        end_time = self.time_format(params['end'])
        session = db_api.get_session()
        query = session.query(models.Net).\
               filter_by(instance_uuid = instance_uuid).\
               filter(models.Net.created_at >= start_time).\
               filter(models.Net.created_at <= end_time).\
               group_by(models.Net.created_at).all()
        result = []
        for item in query:
            result.append(item.to_dict())
        return result

    def get_disk_sample(self, req, instance_uuid):
        params = {}
        params.update(req.GET)
        start_time = self.time_format(params['start'])
        end_time = self.time_format(params['end'])
        session = db_api.get_session()
        query = session.query(models.Disk).\
               filter_by(instance_uuid = instance_uuid).\
               filter(models.Disk.created_at >= start_time).\
               filter(models.Disk.created_at <= end_time).\
               group_by(models.Disk.created_at).all()
        result = []
        for item in query:
            result.append(item.to_dict())
        return result

    def get_cpu_sample(self, req, instance_uuid):
        params = {}
        params.update(req.GET)
        start_time = self.time_format(params['start'])
        end_time = self.time_format(params['end'])
        #session = db_api.get_session()
        session = self.get_session()
        query = session.query(models.Cpu).\
               filter_by(instance_uuid = instance_uuid).\
               filter(models.Cpu.created_at >= start_time).\
               filter(models.Cpu.created_at <= end_time).\
               group_by(models.Cpu.created_at).all()
        result = []
        for item in query:
            result.append(item.to_dict())
        return result

    def get_mem_sample(self, req, instance_uuid):
        params = {}
        params.update(req.GET)
        start_time = self.time_format(params['start'])
        end_time = self.time_format(params['end'])
        session = db_api.get_session()
        query = session.query(models.Mem).\
               filter_by(instance_uuid = instance_uuid).\
               filter(models.Mem.created_at >= start_time).\
               filter(models.Mem.created_at <= end_time).\
               group_by(models.Mem.created_at).all()
        result = []
        for item in query:
            result.append(item.to_dict())
        return result

def create_resource():
    """Images resource factory method"""
    #deserializer = ImageDeserializer()
    #serializer = ImageSerializer()
    return wsgi.Resource(Controller())
