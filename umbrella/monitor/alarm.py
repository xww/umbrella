'''
Created on 2012-10-29

@author: hzzhoushaoyu
'''

import umbrella.common.log as logging
from umbrella.common import local
from umbrella.common import exception
from umbrella import db
from umbrella.db.sqlalchemy import models
from umbrella.common import cfg

LOG = logging.getLogger(__name__)

CHECK_ATTRIBUTES = [
                    "local_gb",
                    "memory_mb",
                    "servers",
                    "vcpus",
                    "floating_ips"
                    ]

opts = [
        cfg.IntOpt("no_replicate_alarm_seconds", default=3600),
        cfg.BoolOpt("alarm_replicate_usage_changed", default=True)
       ]

CONF = cfg.CONF
CONF.register_opts(opts)


class AlarmCheck(object):
    '''
    check whether usage is higher than threshold
    '''
    def __init__(self):
        self.db_api = db.get_api()

    def check_type_usage(self, level, setting_type, type_usage):
        '''
        check specify setting type usage in specify level
        '''
        store = local.dict_store()
        expire = CONF.no_replicate_alarm_seconds
        alarm_replicate = CONF.alarm_replicate_usage_changed
        # check whether need alarm replicated in expire seconds
        latest_alarm_usage = store.get_alarming(level, setting_type,
                                                type_usage, expire)
        if latest_alarm_usage is not None:
            if not (latest_alarm_usage != type_usage and alarm_replicate):
                # if usage not change, not alarm;
                # if changed but not need alarm, not alarm.
                LOG.debug(_("Has alarmed in %(expire)s seconds for "
                            "level %(level)s and setting type %(setting_type)s"
                            " and usage %(type_usage)s..."), locals())
                return
        # need alarm and search for settings
        setting = store.get_setting(level, setting_type)
        if not setting:
            self.db_api.configure_db()
            try:
                setting = self.db_api.setting_get_by_lever_type(level,
                                                                setting_type)
                store.save_setting(level, setting_type, setting)
            except exception.NotFound:
                setting = None
        if not setting or setting.capacity <= 0 or setting.threshold <= 0.0:
            # Note(hzzhoushaoyu): no valid setting has been found in cache
            # and DB return for no alarming
            LOG.info(_("NO setting found for level %(level)s "
                    "and type %(setting_type)s"),
                locals())
            return

        if type_usage > setting.capacity * setting.threshold / 100:
            LOG.debug(_("saving alarming for level %(level)s "
                        "and type %(setting_type)s....."), locals())
            alarming_dict = {
                             "settings_uuid": setting.uuid,
                             "usage": type_usage,
                             }
            self.db_api.alarming_create(alarming_dict)
            store.save_alarming(level, setting_type, type_usage)

    def check_threshold(self, level, usages_dict):
        '''
        check all setting type usages in specify level
        '''
        raise exception.Unimplementation()
