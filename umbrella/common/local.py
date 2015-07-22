# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
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

"""Greenthread local storage of variables using weak references"""

import weakref

from eventlet import corolocal

from umbrella.common import timeutils
import logging

LOG = logging.getLogger(__name__)


class WeakLocal(corolocal.local):
    def __getattribute__(self, attr):
        rval = corolocal.local.__getattribute__(self, attr)
        if rval:
            rval = rval()
        return rval

    def __setattr__(self, attr, value):
        value = weakref.ref(value)
        return corolocal.local.__setattr__(self, attr, value)


class Global(object):

    def get_item(self, cache_dir, key):
        cache = self.store_dict
        if cache_dir not in cache:
            cache.update({cache_dir: {}})
        items_cache = cache[cache_dir]
        ret = items_cache.get(key, None)
        if ret is None:
            return None
        try:
            item, created, timeout = ret
        except (TypeError, ValueError):
            LOG.warn(_("cache %s can not unpack.") % ret)
            return None
        if timeutils.is_older_than(created, timeout):
            items_cache.pop(key, None)
            return None
        return item

    def save_item(self, cache_dir, key, item, timeout=60):
        '''
        :param cache_dir: save directory in cache
        :param key: save key after directory
        :param item: item to save
        :param timeout: cache item is abandoned in timeout seconds.
        '''
        cache = self.store_dict
        if cache_dir not in cache:
            cache.update({cache_dir: {}})
        items_cache = cache[cache_dir]
        items_cache.update({key: (item, timeutils.utcnow(), timeout)})

    def save_setting(self, level, setting_type, setting):
        self.store_dict.update({(level, setting_type): setting})

    def get_setting(self, level, setting_type, default=None):
        ret = self.store_dict.get((level, setting_type))
        if ret is None:
            return default

    def save_alarming(self, level, setting_type, usage):
        self.store_dict.update({('alarm', level, setting_type):
                                    (usage, timeutils.utcnow())})

    def get_alarming(self, level, setting_type, usage, expire):
        '''
        get alarm of NO expire in local dict store.
        return None if not exist or expired.
        '''
        latest_alarm = self.store_dict.get(('alarm', level, setting_type))
        if latest_alarm is None:
            return None
        usage, alarm_time = latest_alarm
        if timeutils.is_older_than(alarm_time, expire):
            # alarm in dict expired
            try:
                self.store_dict.pop(('alarm', level, setting_type))
            except KeyError:
                pass
            return None
        return usage

store = WeakLocal()
# Note(hzzhoushaoyu):should not use _memory directly
# use dict_store() instead
_memory = Global()


def dict_store():
    if not hasattr(_memory, 'store_dict'):
        setattr(_memory, "store_dict", {})
    return _memory
