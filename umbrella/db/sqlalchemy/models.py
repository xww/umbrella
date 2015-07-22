# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
SQLAlchemy models for glance data
"""

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm.util import object_mapper
from sqlalchemy.schema import Column
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import BigInteger
from sqlalchemy.types import Float
from sqlalchemy.types import Boolean
from sqlalchemy.types import DateTime
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.types import Text
from umbrella.common import timeutils
from umbrella.common import utils
import umbrella.common.log as logging

LOG = logging.getLogger(__name__)

BASE = declarative_base()

PLATFORM_LEVEL = 0
HOST_LEVEL = 1
USER_LEVEL = 2
AZ_LEVEL = 3


@compiles(BigInteger, 'sqlite')
def compile_big_int_sqlite(type_, compiler, **kw):
    return 'INTEGER'


class ModelBase(object):
    """Base class for Umbrella Models"""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    __protected_attributes__ = set([
        "id", "created_at", "updated_at", "deleted_at", "deleted"])

    id = Column(Integer(), primary_key=True, nullable=False)
    created_at = Column(DateTime, default=timeutils.utcnow,
                        nullable=False)
    updated_at = Column(DateTime, default=timeutils.utcnow,
                        nullable=False, onupdate=timeutils.utcnow)
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, nullable=False, default=False)

    def save(self, session=None):
        """Save this object"""
        if session is None:
            LOG.error(_("method deprecated as no session passed in."))
            return
        session.add(self)
        session.flush()

    def delete(self, session=None):
        """Delete this object"""
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)

    def update(self, values):
        """dict.update() behaviour."""
        for k, v in values.iteritems():
            self[k] = v

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        self._i = iter(object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        return self.__dict__.copy()


class Alarming(BASE, ModelBase):
    """Represents an alarming info in the datastore"""
    __tablename__ = 'alarming'
    __updatable_attributes__ = set([
        "done", "readed", "read_user_id"])

    settings_uuid = Column(String(36), ForeignKey('settings.uuid'),
                      nullable=False)
    usage = Column(Integer(), default=0)
    done = Column(Boolean(), default=False)
    readed = Column(Boolean(), default=False)
    read_user_id = Column(String(255))


class Settings(BASE, ModelBase):
    """Represents an setting in the datastore"""
    __tablename__ = 'settings'
    __table_args__ = (UniqueConstraint('uuid'), {})

    uuid = Column(String(36), default=utils.generate_uuid)
    level = Column(Integer(), default=-1)
    type = Column(String(30))
    capacity = Column(Integer(), default=0)
    threshold = Column(Float(), default=0.0)
    alarm_title = Column(Text)
    alarm_content = Column(Text)
    enable = Column(Boolean(), nullable=False, default=True)
    alarming = relationship(Alarming, backref=backref('setting'))


def register_models(engine):
    """
    Creates database tables for all models with the given engine
    """
    models = (Alarming, Settings)
    for model in models:
        model.metadata.create_all(engine)


def unregister_models(engine):
    """
    Drops database tables for all models with the given engine
    """
    models = (Alarming, Settings)
    for model in models:
        model.metadata.drop_all(engine)
