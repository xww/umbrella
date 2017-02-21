# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2010-2011 OpenStack Foundation
# Copyright 2012 Justin Santa Barbara
# Copyright 2013 IBM Corp.
# Copyright 2015 Mirantis, Inc.
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


"""Defines interface for DB access."""

import threading

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db.sqlalchemy import session
from oslo_log import log as logging
#from oslo_utils import timeutils
# NOTE(jokke): simplified transition to py3, behaves like py2 xrange
from six.moves import range
import sqlalchemy
import sqlalchemy.sql as sa_sql

from umbrella.common import exception
from umbrella.db.sqlalchemy import models
from umbrella import i18n

BASE = models.BASE
sa_logger = None
LOG = logging.getLogger(__name__)
_ = i18n._
_LW = i18n._LW


STATUSES = ['active', 'saving', 'queued', 'killed', 'pending_delete',
            'deleted', 'deactivated']

CONF = cfg.CONF

_FACADE = None
_LOCK = threading.Lock()


def _retry_on_deadlock(exc):
    """Decorator to retry a DB API call if Deadlock was received."""

    if isinstance(exc, db_exception.DBDeadlock):
        LOG.warn(_LW("Deadlock detected. Retrying..."))
        return True
    return False


def _create_facade_lazily():
    global _LOCK, _FACADE
    if _FACADE is None:
        with _LOCK:
            if _FACADE is None:
                _FACADE = session.EngineFacade.from_config(CONF)

                #if CONF.profiler.enabled and CONF.profiler.trace_sqlalchemy:
                #    osprofiler.sqlalchemy.add_tracing(sqlalchemy,
                #                                      _FACADE.get_engine(),
                #                                      "db")
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(autocommit=True, expire_on_commit=False):
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)


def clear_db_env():
    """
    Unset global configuration variables for database.
    """
    global _FACADE
    _FACADE = None


def _paginate_query(query, model, limit, sort_keys, marker=None,
                    sort_dir=None, sort_dirs=None):
    """Returns a query with sorting / pagination criteria added.

    Pagination works by requiring a unique sort_key, specified by sort_keys.
    (If sort_keys is not unique, then we risk looping through values.)
    We use the last row in the previous page as the 'marker' for pagination.
    So we must return values that follow the passed marker in the order.
    With a single-valued sort_key, this would be easy: sort_key > X.
    With a compound-values sort_key, (k1, k2, k3) we must do this to repeat
    the lexicographical ordering:
    (k1 > X1) or (k1 == X1 && k2 > X2) or (k1 == X1 && k2 == X2 && k3 > X3)

    We also have to cope with different sort_directions.

    Typically, the id of the last row is used as the client-facing pagination
    marker, then the actual marker object must be fetched from the db and
    passed in to us as marker.

    :param query: the query object to which we should add paging/sorting
    :param model: the ORM model class
    :param limit: maximum number of items to return
    :param sort_keys: array of attributes by which results should be sorted
    :param marker: the last item of the previous page; we returns the next
                    results after this value.
    :param sort_dir: direction in which results should be sorted (asc, desc)
    :param sort_dirs: per-column array of sort_dirs, corresponding to sort_keys

    :rtype: sqlalchemy.orm.query.Query
    :return: The query with sorting/pagination added.
    """

    if 'id' not in sort_keys:
        # TODO(justinsb): If this ever gives a false-positive, check
        # the actual primary key, rather than assuming its id
        LOG.warn(_LW('Id not in sort_keys; is sort_keys unique?'))

    assert(not (sort_dir and sort_dirs))

    # Default the sort direction to ascending
    if sort_dirs is None and sort_dir is None:
        sort_dir = 'asc'

    # Ensure a per-column sort direction
    if sort_dirs is None:
        sort_dirs = [sort_dir for _sort_key in sort_keys]

    assert(len(sort_dirs) == len(sort_keys))

    # Add sorting
    for current_sort_key, current_sort_dir in zip(sort_keys, sort_dirs):
        sort_dir_func = {
            'asc': sqlalchemy.asc,
            'desc': sqlalchemy.desc,
        }[current_sort_dir]

        try:
            sort_key_attr = getattr(model, current_sort_key)
        except AttributeError:
            raise exception.InvalidSortKey()
        query = query.order_by(sort_dir_func(sort_key_attr))

    default = ''  # Default to an empty string if NULL

    # Add pagination
    if marker is not None:
        marker_values = []
        for sort_key in sort_keys:
            v = getattr(marker, sort_key)
            if v is None:
                v = default
            marker_values.append(v)

        # Build up an array of sort criteria as in the docstring
        criteria_list = []
        for i in range(len(sort_keys)):
            crit_attrs = []
            for j in range(i):
                model_attr = getattr(model, sort_keys[j])
                default = None if isinstance(
                    model_attr.property.columns[0].type,
                    sqlalchemy.DateTime) else ''
                attr = sa_sql.expression.case([(model_attr != None,
                                              model_attr), ],
                                              else_=default)
                crit_attrs.append((attr == marker_values[j]))

            model_attr = getattr(model, sort_keys[i])
            default = None if isinstance(model_attr.property.columns[0].type,
                                         sqlalchemy.DateTime) else ''
            attr = sa_sql.expression.case([(model_attr != None,
                                          model_attr), ],
                                          else_=default)
            if sort_dirs[i] == 'desc':
                crit_attrs.append((attr < marker_values[i]))
            elif sort_dirs[i] == 'asc':
                crit_attrs.append((attr > marker_values[i]))
            else:
                raise ValueError(_("Unknown sort direction, "
                                   "must be 'desc' or 'asc'"))

            criteria = sa_sql.and_(*crit_attrs)
            criteria_list.append(criteria)

        f = sa_sql.or_(*criteria_list)
        query = query.filter(f)

    if limit is not None:
        query = query.limit(limit)

    return query


def get_one_net():
    session = get_session()
    query = session.query(models.Net)
    return query.first()


def add_net_sample(sample):
    session = get_session()
    with session.begin():
        value = models.Net(
           instance_uuid=sample['instance_uuid'],
            tenant_id=sample['tenant_id'],
            total_packets_rate_rx=sample['rx_packets_rate'],
            total_bytes_rate_rx=sample['rx_bytes_rate'],
            total_packets_rate_tx=sample['tx_packets_rate'],
            total_bytes_rate_tx=sample['tx_bytes_rate'],
            pubnet_bytes_tx=sample['pubnet_bytes_tx'],
            pubnet_bytes_rx=sample['pubnet_bytes_rx'],
            pubnet_packets_tx=sample['pubnet_packets_tx'],
            pubnet_packets_rx=sample['pubnet_packets_rx'],
            
        )

        value.save(session=session)
        #session.commit()

def add_disk_sample(sample):
    session = get_session()
    with session.begin():
        value = models.Disk(
           instance_uuid=sample['instance_uuid'],
            tenant_id=sample['tenant_id'],
            rd_req_rate=sample['rd_req_rate'],
            rd_bytes_rate=sample['rd_bytes_rate'],
            wr_req_rate=sample['wr_req_rate'],
            wr_bytes_rate=sample['wr_bytes_rate']
        )

        value.save(session=session)
        #session.commit()


def add_cpu_sample(sample):
    session = get_session()
    with session.begin():
        value = models.Cpu(
           instance_uuid=sample['instance_uuid'],
            tenant_id=sample['tenant_id'],
            cpu_load=sample['cpu_load'],
        )

        value.save(session=session)
        #session.commit()


def add_mem_sample(sample):
    session = get_session()
    with session.begin():
        value = models.Mem(
           instance_uuid=sample['instance_uuid'],
            tenant_id=sample['tenant_id'],
            mem_used=sample['mem_used'],
        )
        value.save(session=session)
        #session.commit()
