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

from sqlalchemy.schema import (Column, MetaData, Table)

from umbrella.db.sqlalchemy.migrate_repo.schema import (
    Boolean, DateTime, Integer, String, Text, create_tables, drop_tables)  # noqa

def define_net_table(meta):
    net = Table('net',
                   meta,
                   Column('id', Integer(), primary_key=True, autoincrement=True,
                          nullable=False),
                   Column('instance_uuid', String(40), nullable=False,
                          index=True),
                   Column('tenant_id', String(40), nullable=False, index=True),
                   Column('total_packets_rate_rx', Integer()),
                   Column('total_bytes_rate_rx', Integer()),
                   Column('total_packets_rate_tx', Integer()),
                   Column('total_bytes_rate_tx', Integer()),
                   Column('pubnet_bytes_tx', Integer()),
                   Column('pubnet_bytes_rx', Integer()),
                   Column('pubnet_packets_tx', Integer()),
                   Column('pubnet_packets_rx', Integer()),
                   Column('pubnet_bytes_rate_tx', Integer()),
                   Column('pubnet_bytes_rate_rx', Integer()),
                   Column('pubnet_packets_rate_tx', Integer()),
                   Column('pubnet_packets_rate_rx', Integer()),
                   Column('created_at', DateTime(), nullable=False),
                   Column('updated_at', DateTime()),
                   mysql_engine='InnoDB',
                   extend_existing=True)

    return net


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    tables = [define_net_table(meta)]
    create_tables(tables)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    tables = [define_net_table(meta)]
    drop_tables(tables)
