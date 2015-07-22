# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2010-2011 OpenStack LLC.
# Copyright 2012 Justin Santa Barbara
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
Defines interface for DB access
"""

import logging
import time

import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm
import sqlalchemy.sql

from umbrella.common import exception
from umbrella.db.sqlalchemy import migration
from umbrella.db.sqlalchemy import models
from umbrella.common import cfg
import umbrella.common.log as os_logging
from umbrella.common import timeutils


_ENGINE = None
_MAKER = None
_MAX_RETRIES = None
_RETRY_INTERVAL = None
BASE = models.BASE
sa_logger = None
LOG = os_logging.getLogger(__name__)


db_opts = [
    cfg.IntOpt('sql_idle_timeout', default=3600),
    cfg.IntOpt('sql_max_retries', default=10),
    cfg.IntOpt('sql_retry_interval', default=1),
    cfg.BoolOpt('db_auto_create', default=False),
    ]

CONF = cfg.CONF
CONF.register_opts(db_opts)


def ping_listener(dbapi_conn, connection_rec, connection_proxy):

    """
    Ensures that MySQL connections checked out of the
    pool are alive.

    Borrowed from:
    http://groups.google.com/group/sqlalchemy/msg/a4ce563d802c929f
    """

    try:
        dbapi_conn.cursor().execute('select 1')
    except dbapi_conn.OperationalError, ex:
        if ex.args[0] in (2006, 2013, 2014, 2045, 2055):
            msg = 'Got mysql server has gone away: %s' % ex
            LOG.warn(msg)
            raise sqlalchemy.exc.DisconnectionError(msg)
        else:
            raise


def configure_db():
    """
    Establish the database, create an engine if needed, and
    register the models.
    """
    global _ENGINE, sa_logger, _MAX_RETRIES, _RETRY_INTERVAL
    if not _ENGINE:
        sql_connection = CONF.sql_connection
        _MAX_RETRIES = CONF.sql_max_retries
        _RETRY_INTERVAL = CONF.sql_retry_interval
        connection_dict = sqlalchemy.engine.url.make_url(sql_connection)
        engine_args = {'pool_recycle': CONF.sql_idle_timeout,
                       'echo': False,
                       'convert_unicode': True
                       }

        try:
            _ENGINE = sqlalchemy.create_engine(sql_connection, **engine_args)

            if 'mysql' in connection_dict.drivername:
                sqlalchemy.event.listen(_ENGINE, 'checkout', ping_listener)

            _ENGINE.connect = wrap_db_error(_ENGINE.connect)
            _ENGINE.connect()
        except Exception, err:
            msg = _("Error configuring database with supplied "
                    "sql_connection '%(sql_connection)s'. "
                    "Got error:\n%(err)s") % locals()
            LOG.error(msg)
            raise

        sa_logger = logging.getLogger('sqlalchemy.engine')
        if CONF.debug:
            sa_logger.setLevel(logging.DEBUG)

        if CONF.db_auto_create:
            LOG.info('auto-creating umbrella DB')
            models.register_models(_ENGINE)
            try:
                migration.version_control()
            except exception.DatabaseMigrationError:
                # only arises when the DB exists and is under version control
                pass
        else:
            LOG.info('not auto-creating umbrella DB')


def get_session(autocommit=True, expire_on_commit=False):
    """Helper method to grab session"""
    global _MAKER
    if not _MAKER:
        assert _ENGINE
        _MAKER = sqlalchemy.orm.sessionmaker(bind=_ENGINE,
                                             autocommit=autocommit,
                                             expire_on_commit=expire_on_commit)
    return _MAKER()


def is_db_connection_error(args):
    """Return True if error in connecting to db."""
    conn_err_codes = ('2002', '2003', '2006')
    for err_code in conn_err_codes:
        if args.find(err_code) != -1:
            return True
    return False


def wrap_db_error(f):
    """Retry DB connection. Copied from nova and modified."""
    def _wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlalchemy.exc.OperationalError, e:
            if not is_db_connection_error(e.args[0]):
                raise

            remaining_attempts = _MAX_RETRIES
            while True:
                LOG.warning(_('SQL connection failed. %d attempts left.'),
                                remaining_attempts)
                remaining_attempts -= 1
                time.sleep(_RETRY_INTERVAL)
                try:
                    return f(*args, **kwargs)
                except sqlalchemy.exc.OperationalError, e:
                    if (remaining_attempts == 0 or
                        not is_db_connection_error(e.args[0])):
                        raise
                except sqlalchemy.exc.DBAPIError:
                    raise
        except sqlalchemy.exc.DBAPIError:
            raise
    _wrap.func_name = f.func_name
    return _wrap


def setting_create(values):
    """Create an setting from the values dictionary."""
    return _setting_update(values, None)


def setting_update(setting_uuid, values):
    """
    Set the given properties on an setting and update it.

    :raises NotFound if setting does not exist.
    """
    return _setting_update(values, setting_uuid)


def setting_destroy(setting_uuid):
    """Destroy the setting or raise if it does not exist."""
    session = get_session()
    with session.begin():
        setting_ref = setting_get(setting_uuid, session=session)
        setting_ref.delete(session=session)
        return setting_ref


def setting_get(setting_uuid, session=None, force_show_deleted=False):
    """Get an setting or raise if it does not exist."""
    session = session or get_session()

    try:
        query = session.query(models.Settings).\
                filter_by(uuid=setting_uuid)

        if not force_show_deleted:
            query = query.filter_by(deleted=False)

        setting = query.one()

    except sqlalchemy.orm.exc.NoResultFound:
        raise exception.NotFound("No setting found with UUID %s" %
                                 setting_uuid)

    return setting


def setting_get_by_lever_type(level, setting_type, session=None):
    """Get an setting or raise if it does not exist."""
    session = session or get_session()

    try:
        query = session.query(models.Settings).\
                options(sqlalchemy.orm.joinedload(models.Settings.alarming)).\
                filter_by(level=level).\
                filter_by(type=setting_type).\
                filter_by(deleted=False)

        setting = query.one()

    except sqlalchemy.orm.exc.NoResultFound:
        raise exception.NotFound("No setting found with level %(level)s"
                                 " and type %(setting_type)s" % locals())

    return setting


def paginate_query(query, model, limit, sort_keys, marker=None,
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
        LOG.warn(_('Id not in sort_keys; is sort_keys unique?'))

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

    # Add pagination
    if marker is not None:
        marker_values = []
        for sort_key in sort_keys:
            v = getattr(marker, sort_key)
            marker_values.append(v)

        # Build up an array of sort criteria as in the docstring
        criteria_list = []
        for i in xrange(0, len(sort_keys)):
            crit_attrs = []
            for j in xrange(0, i):
                model_attr = getattr(model, sort_keys[j])
                crit_attrs.append((model_attr == marker_values[j]))

            model_attr = getattr(model, sort_keys[i])
            if sort_dirs[i] == 'desc':
                crit_attrs.append((model_attr < marker_values[i]))
            elif sort_dirs[i] == 'asc':
                crit_attrs.append((model_attr > marker_values[i]))
            else:
                raise ValueError(_("Unknown sort direction, "
                                   "must be 'desc' or 'asc'"))

            criteria = sqlalchemy.sql.and_(*crit_attrs)
            criteria_list.append(criteria)

        f = sqlalchemy.sql.or_(*criteria_list)
        query = query.filter(f)

    if limit is not None:
        query = query.limit(limit)

    return query


def setting_get_all(filters=None, marker=None, limit=None,
                  sort_key='created_at', sort_dir='desc'):
    """
    Get all settings that match zero or more filters.

    :param filters: dict of filter keys and values.
    :param marker: setting uuid after which to start page
    :param limit: maximum number of settings to return
    :param sort_key: setting attribute by which results should be sorted
    :param sort_dir: direction in which results should be sorted (asc, desc)
    """
    filters = filters or {}

    session = get_session()
    query = session.query(models.Settings).\
            options(sqlalchemy.orm.joinedload(models.Settings.alarming))

    showing_deleted = False
    if 'changes-since' in filters:
        # normalize timestamp to UTC, as sqlalchemy doesn't appear to
        # respect timezone offsets
        changes_since = timeutils.normalize_time(filters.pop('changes-since'))
        query = query.filter(models.Settings.updated_at > changes_since)
        showing_deleted = True

    if 'deleted' in filters:
        deleted_filter = filters.pop('deleted')
        query = query.filter_by(deleted=deleted_filter)
        showing_deleted = deleted_filter

    for (k, v) in filters.items():
        if v is not None:
            key = k
            if k.endswith('_min') or k.endswith('_max'):
                key = key[0:-4]
                try:
                    v = int(v)
                except ValueError:
                    msg = _("Unable to filter on a range "
                            "with a non-numeric value.")
                    raise exception.InvalidFilterRangeValue(msg)

            if k.endswith('_min'):
                query = query.filter(getattr(models.Settings, key) >= v)
            elif k.endswith('_max'):
                query = query.filter(getattr(models.Settings, key) <= v)
            elif hasattr(models.Settings, key):
                query = query.filter(getattr(models.Settings, key) == v)

    marker_setting = None
    if marker is not None:
        marker_setting = setting_get(marker,
                                 force_show_deleted=showing_deleted)

    query = paginate_query(query, models.Settings, limit,
                           [sort_key, 'created_at', 'id'],
                           marker=marker_setting,
                           sort_dir=sort_dir)

    return query.all()


def _drop_protected_attrs(model_class, values):
    """
    Removed protected attributes from values dictionary using the models
    __protected_attributes__ field.
    """
    for attr in model_class.__protected_attributes__:
        if attr in values:
            del values[attr]


def _update_values(setting_ref, values):
    for k in values.keys():
        if getattr(setting_ref, k) != values[k]:
            setattr(setting_ref, k, values[k])


def _setting_update(values, setting_uuid):
    """
    Used internally by setting_create and setting_update

    :param values: A dict of attributes to set
    :param setting_uuid: If None, create the setting, otherwise,
                        find and update it
    """
    session = get_session()
    with session.begin():
        # should not update uuid
        values.pop("uuid", None)
        # Remove the properties passed in the values mapping. We
        # handle properties separately from base setting attributes,
        # and leaving properties in the values mapping will cause
        # a SQLAlchemy model error because SQLAlchemy expects the
        # properties attribute of an setting model to be a list and
        # not a dict.
        if setting_uuid:
            setting_ref = setting_get(setting_uuid, session=session)
        else:
            setting_ref = models.Settings()
        if setting_ref:
            # Don't drop created_at if we're passing it in...
            _drop_protected_attrs(models.Settings, values)
            values['updated_at'] = timeutils.utcnow()
        setting_ref.update(values)
        # Should not set duplicate level and type pair
        if setting_ref.level is not None and setting_ref.type is not None:
            try:
                setting_dup = setting_get_by_lever_type(setting_ref.level,
                                                    setting_ref.type)
            except exception.NotFound:
                setting_dup = None
            if setting_dup and not setting_uuid:
                raise exception.Duplicate(_("Setting level(%s)"
                                          "-type(%s) pair already exists!") % \
                                          (setting_ref.level,
                                           setting_ref.type))
        # Validate the attributes before we go any further. From my
        # investigation, the @validates decorator does not validate
        # on new records, only on existing records, which is, well,
        # idiotic.
        _update_values(setting_ref, values)

        try:
            setting_ref.save(session=session)
        except sqlalchemy.exc.IntegrityError:
            raise exception.Duplicate(_("Setting uuid already exists!"))

    return setting_get(setting_ref.uuid)


def alarming_create(values, session=None):
    """Create an Alarming object"""
    session = session if session else get_session()
    alarming_ref = models.Alarming()
    return _alarming_update(alarming_ref, values, session=session)


def _alarming_update(alarming_ref, values, session=None):
    with session.begin():
        _drop_protected_attrs(models.Alarming, values)
        alarming_ref.update(values)
        alarming_ref.save(session=session)
        return alarming_ref


def alarming_update(alarm_id, values, session=None):
    '''
    update alarm values.
    if values contain unable updating values, raise UnableUpdateValue.
    '''
    session = session or get_session()

    for key in values.keys():
        if key not in models.Alarming.__updatable_attributes__:
            raise exception.UnableUpdateValue(_("Unable to update '%(key)s'.")
                                              % locals())
    alarm_ref = alarming_get(alarm_id, session)
    return _alarming_update(alarm_ref, values, session)


def _alarming_delete(alarming_ref, session=None):
    alarming_ref.delete(session=session)


def alarming_delete(alarming_id, session=None):
    session = session or get_session()
    with session.begin():
        alarming_ref = alarming_get(alarming_id, session)
        _alarming_delete(alarming_ref, session)
        return alarming_ref


def alarmings_clear(session=None):
    session = session or get_session()
    with session.begin():
        for alarm_ref in alarming_get_all(filters={'deleted': False},
                                        session=session):
            _alarming_delete(alarm_ref, session)


def alarming_get(alarming_id, session=None, force_show_deleted=False):
    """Get an alarming or raise if it does not exist."""
    session = session or get_session()

    try:
        query = session.query(models.Alarming).\
                options(sqlalchemy.orm.joinedload(models.Alarming.setting)).\
                filter_by(id=alarming_id)

        if not force_show_deleted:
            query = query.filter_by(deleted=False)

        alarming = query.one()

    except sqlalchemy.orm.exc.NoResultFound:
        raise exception.NotFound("No alarming found with ID %s" %
                                 alarming_id)
    return alarming


def alarming_get_all(filters=None, marker=None, limit=None,
                  sort_key='created_at', sort_dir='desc', session=None):
    """
    Get all alarmings that match zero or more filters.

    :param filters: dict of filter keys and values.
    :param marker: alarming id after which to start page
    :param limit: maximum number of alarmings to return
    :param sort_key: alarming attribute by which results should be sorted
    :param sort_dir: direction in which results should be sorted (asc, desc)
    """
    filters = filters or {}

    session = session or get_session()
    query = session.query(models.Alarming).\
            options(sqlalchemy.orm.joinedload(models.Alarming.setting))

    showing_deleted = False
    if 'changes-since' in filters:
        # normalize timestamp to UTC, as sqlalchemy doesn't appear to
        # respect timezone offsets
        changes_since = timeutils.normalize_time(filters.pop('changes-since'))
        query = query.filter(models.Alarming.updated_at > changes_since)
        showing_deleted = True

    if 'deleted' in filters:
        deleted_filter = filters.pop('deleted')
        query = query.filter_by(deleted=deleted_filter)
        showing_deleted = deleted_filter

    if 'readed' in filters:
        query = query.filter_by(readed=filters.pop('readed'))

    if 'done' in filters:
        query = query.filter_by(done=filters.pop('done'))

    if 'setting-uuid' in filters:
        query = query.filter_by(settings_uuid=filters.pop('setting-uuid'))

    marker_alarming = None
    if marker is not None:
        marker_alarming = alarming_get(marker,
                                       force_show_deleted=showing_deleted)

    query = paginate_query(query, models.Alarming, limit,
                           [sort_key, 'created_at', 'id'],
                           marker=marker_alarming,
                           sort_dir=sort_dir)

    return query.all()
