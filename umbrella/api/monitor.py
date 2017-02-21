'''
Created on 2012-10-29

@author: hzzhoushaoyu
'''

import urllib
import json
from webob import exc

from umbrella.common import wsgi
import umbrella.common.log as logging
from umbrella.common import exception
from umbrella.common import local
from umbrella.common import cfg
from umbrella.common import utils
import umbrella.db

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Controller():

    def __init__(self):
        db_api = umbrella.db.get_api()
        db_api.configure_db()
        self.db_api = db_api

    def list_settings(self, req, filters={}, sort_key='created_at',
                      sort_dir='desc'):
        '''
        list all settings not deleted and sorted by sort_key
        '''
        try:
            settings = self.db_api.setting_get_all(filters=filters,
                                        sort_key=sort_key,
                                        sort_dir=sort_dir)
        except exception.InvalidFilterRangeValue as e:
            raise exc.HTTPBadRequest(explanation=unicode(e))
        except exception.InvalidSortKey as e:
            raise exc.HTTPBadRequest(explanation=unicode(e))
        except exception.NotFound as e:
            raise exc.HTTPBadRequest(explanation=unicode(e))
        return {
                'settings': [make_setting_dict(i) for i in settings]
               }

    def get_setting_by_uuid(self, req, uuid):
        '''
        get setting by level and type
        '''
        try:
            setting = self.db_api.setting_get(uuid)
        except exception.NotFound as e:
            raise exc.HTTPBadRequest(explanation=unicode(e))
        return make_setting_dict(setting)

    def get_setting_by_level_type(self, req, level, setting_type):
        '''
        get setting by uuid
        '''
        try:
            setting = self.db_api.setting_get_by_lever_type(level,
                                                            setting_type)
        except exception.NotFound as e:
            raise exc.HTTPBadRequest(explanation=unicode(e))
        return make_setting_dict(setting)

    @utils.require_admin_context
    def save_setting(self, req, body, uuid=None):
        if not uuid:
            setting = self.db_api.setting_create(body)
        else:
            setting = self.db_api.setting_update(uuid, body)
        #save setting in local dict store
        local_dict = local.dict_store()
        local_dict.save_setting(setting.level, setting.type, setting)
        return make_setting_dict(setting)

    @utils.require_admin_context
    def destroy_setting(self, req, uuid):
        self.db_api.setting_destroy(uuid)

    def list_alarms(self, req, marker=None, limit=None,
                sort_key='created_at', sort_dir='desc', filters={}):
        if limit is None:
            limit = CONF.limit_param_default
        limit = min(CONF.api_limit_max, limit)

        alarmings = self.db_api.alarming_get_all(filters=filters,
                            marker=marker, limit=limit,
                            sort_key=sort_key, sort_dir=sort_dir)
        result = dict(alarms=alarmings)
        if len(alarmings) != 0 and len(alarmings) == limit:
            result['next_marker'] = alarmings[-1]['id']
        return result

    def get_alarm(self, req, alarm_id):
        alarm_ref = self.db_api.alarming_get(alarm_id, force_show_deleted=True)
        result = make_alarm_dict(alarm_ref)
        return result

    @utils.require_admin_context
    def update_alarm(self, req, alarm_id, body):
        alarm_ref = self.db_api.alarming_update(alarm_id, body)
        result = make_alarm_dict(alarm_ref)
        return result

    @utils.require_admin_context
    def delete_alarm(self, req, alarm_id):
        self.db_api.alarming_delete(alarm_id)

    @utils.require_admin_context
    def clear_alarms(self, req):
        self.db_api.alarmings_clear()


class RequestDeserializer(wsgi.JSONRequestDeserializer):

    def _validate_sort_dir(self, sort_dir):
        if sort_dir not in ['asc', 'desc']:
            msg = _('Invalid sort direction: %s' % sort_dir)
            raise exc.HTTPBadRequest(explanation=msg)

        return sort_dir

    def _validate_limit(self, limit):
        try:
            limit = int(limit)
        except ValueError:
            msg = _("limit param must be an integer")
            raise exc.HTTPBadRequest(explanation=msg)

        if limit < 0:
            msg = _("limit param must be positive")
            raise exc.HTTPBadRequest(explanation=msg)

        return limit

    def _str_to_bool(self, value):
        if value is not None:
            if value in ["1", 'true', 'True', "0", 'false', 'False']:
                return value in ["1", 'true', 'True']
            else:
                msg = _('Invalid deleted value: %s') % value
                raise exc.HTTPBadRequest(explanation=msg)

    def _get_filters(self, filters):
        bool_key = ['deleted', 'readed', 'done']
        for key in bool_key:
            if key in filters.keys():
                filters[key] = self._str_to_bool(filters[key])
        return filters

    def list_settings(self, request):
        params = request.params.copy()
        sort_dir = params.pop('sort_dir', 'desc')
        query_params = {
            'sort_key': params.pop('sort_key', 'created_at'),
            'sort_dir': self._validate_sort_dir(sort_dir),
            'filters': self._get_filters(params),
        }

        return query_params

    def list_alarms(self, request):
        params = request.params.copy()
        limit = params.pop('limit', None)
        marker = params.pop('marker', None)
        sort_dir = params.pop('sort_dir', 'desc')
        query_params = {
            'sort_key': params.pop('sort_key', 'created_at'),
            'sort_dir': self._validate_sort_dir(sort_dir),
            'filters': self._get_filters(params),
        }

        if marker is not None:
            query_params['marker'] = marker

        if limit is not None:
            query_params['limit'] = self._validate_limit(limit)

        return query_params


class ResponseSerializer(wsgi.JSONResponseSerializer):

    def list_alarms(self, response, result):
        params = dict(response.request.params)
        params.pop('marker', None)
        query = urllib.urlencode(params)
        body = {
               'alarms': [make_alarm_dict(i) for i in result['alarms']],
               'first': '/alarms'
        }
        if query:
            body['first'] = '%s?%s' % (body['first'], query)
        if 'next_marker' in result:
            params['marker'] = result['next_marker']
            next_query = urllib.urlencode(params)
            body['next'] = '/alarms?%s' % next_query
        response.body = self.to_json(body)
        response.content_type = 'application/json'


def _fetch_attrs(d, attrs):
        return dict([(a, d[a]) for a in attrs
                    if a in d.keys()])


def make_setting_dict(setting):
    """
    Create a dict representation of an setting which we can use to
    serialize the setting.
    """
    settings_dict = _fetch_attrs(setting, umbrella.db.SETTING_ATTRS)
    return settings_dict


def make_alarm_dict(alarm):
    """
    Create a dict representation of an alarm which we can use to
    serialize the setting.
    """
    alarm_dict = _fetch_attrs(alarm, umbrella.db.ALARM_ATTRS)
    setting = make_setting_dict(alarm_dict['setting'])
    for key in setting:
        alarm_dict['setting-%s' % key] = setting[key]
    alarm_dict.pop("setting")
    return alarm_dict


def create_resource():
    return wsgi.Resource(Controller(), serializer=ResponseSerializer(),
                          deserializer=RequestDeserializer())
