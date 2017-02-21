# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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
SQLAlchemy models for umbrella data
"""

import uuid

from oslo_db.sqlalchemy import models
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy import sql
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy import UniqueConstraint

from umbrella.common import timeutils as our_timeutils

BASE = declarative_base()


@compiles(BigInteger, 'sqlite')
def compile_big_int_sqlite(type_, compiler, **kw):
    return 'INTEGER'


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string"""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = jsonutils.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = jsonutils.loads(value)
        return value


class UmbrellaBase(models.ModelBase, models.TimestampMixin):
    """Base class for Glance Models."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    __protected_attributes__ = set([
        "created_at", "updated_at"])

    def save(self, session=None):
        from umbrella.db.sqlalchemy import api as db_api
        super(UmbrellaBase, self).save(session or db_api.get_session())

    created_at = Column(DateTime, default=lambda: our_timeutils.utc_to_local(
                        timeutils.utcnow()), nullable=False)
    # TODO(vsergeyev): Column `updated_at` have no default value in
    #                  openstack common code. We should decide, is this value
    #                  required and make changes in oslo (if required) or
    #                  in umbrella (if not).
    updated_at = Column(DateTime, default=lambda: our_timeutils.utc_to_local(
                        timeutils.utcnow()), nullable=True, onupdate=lambda: \
                        our_timeutils.utc_to_local(timeutils.utcnow()))
    # TODO(boris-42): Use SoftDeleteMixin instead of deleted Column after
    #                 migration that provides UniqueConstraints and change
    #                 type of this column.
    #deleted_at = Column(DateTime)
    #deleted = Column(Boolean, nullable=False, default=False)

    #def delete(self, session=None):
    #    """Delete this object."""
    #    self.deleted = True
    #    self.deleted_at = timeutils.utcnow()
    #    self.save(session=session)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        d = self.__dict__.copy()
        # NOTE(flaper87): Remove
        # private state instance
        # It is not serializable
        # and causes CircularReference
        d.pop("_sa_instance_state")
        return d


class Net(BASE, UmbrellaBase):
    __tablename__ = 'net'
    __table_args__ = (Index('ix_instance_uuid', 'instance_uuid'),
                      Index('ix_tenant_id', 'tenant_id'),
                      Index('ix_id', 'id'))

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_uuid = Column(String(30), nullable=False)
    tenant_id = Column(String(30), nullable=False)
    total_packets_rate_rx = Column(Integer)
    total_bytes_rate_rx = Column(Integer)
    total_packets_rate_tx = Column(Integer)
    total_bytes_rate_tx = Column(Integer)
    pubnet_bytes_tx = Column(Integer)
    pubnet_bytes_rx = Column(Integer)
    pubnet_packets_tx = Column(Integer)
    pubnet_packets_rx = Column(Integer)
    pubnet_bytes_rate_tx = Column(Integer)
    pubnet_bytes_rate_rx = Column(Integer)
    pubnet_packets_rate_tx = Column(Integer)
    pubnet_packets_rate_rx = Column(Integer)


class Disk(BASE, UmbrellaBase):
    __tablename__ = 'disk'
    __table_args__ = (Index('ix_instance_uuid', 'instance_uuid'),
                      Index('ix_tenant_id', 'tenant_id'),
                      Index('ix_id', 'id'))

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_uuid = Column(String(30), nullable=False)
    tenant_id = Column(String(30), nullable=False)
    rd_req_rate = Column(Integer)
    rd_bytes_rate = Column(Integer)
    wr_req_rate = Column(Integer)
    wr_bytes_rate = Column(Integer)


class Cpu(BASE, UmbrellaBase):
    __tablename__ = 'cpu'
    __table_args__ = (Index('ix_instance_uuid', 'instance_uuid'),
                      Index('ix_tenant_id', 'tenant_id'),
                      Index('ix_id', 'id'))

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_uuid = Column(String(30), nullable=False)
    tenant_id = Column(String(30), nullable=False)
    cpu_load = Column(Integer)


class Mem(BASE, UmbrellaBase):
    """Represents an image in the datastore."""
    __tablename__ = 'mem'
    __table_args__ = (Index('ix_instance_uuid', 'instance_uuid'),
                      Index('ix_tenant_id', 'tenant_id'),
                      Index('ix_id', 'id'))

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_uuid = Column(String(30), nullable=False)
    tenant_id = Column(String(30), nullable=False)
    mem_used = Column(Integer)


    pubnet_bytes_tx = Column(Integer)
    pubnet_bytes_rx = Column(Integer)
    pubnet_packets_tx = Column(Integer)
    pubnet_packets_rx = Column(Integer)
    pubnet_bytes_rate_tx = Column(Integer)
    pubnet_bytes_rate_rx = Column(Integer)
    pubnet_packets_rate_tx = Column(Integer)
    pubnet_packets_rate_rx = Column(Integer)
