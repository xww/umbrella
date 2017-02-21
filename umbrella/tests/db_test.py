'''
Created on 2012-11-6

@author: hzzhoushaoyu
'''

import unittest
from umbrella.common import cfg
from umbrella.common import exception
from umbrella import db
from umbrella.db.sqlalchemy import models

from umbrella.tests import base

CONF = cfg.CONF

DB_API = db.get_api()


class SqlSettingTest(base.IsolatedUnitTest):

    def setUp(self):
        base.IsolatedUnitTest.setUp(self)
        DB_API.configure_db()
        setting_platform_vcpus = dict({"enable": True,
                        "deleted": False,
                        "level": models.PLATFORM_LEVEL,
                        "type": "vcpus",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        setting_host_local = dict({"enable": True,
                        "deleted": False,
                        "level": models.HOST_LEVEL,
                        "type": "local_gb",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        self.setting_platform_vcpus = DB_API.setting_create(
                                                    setting_platform_vcpus)
        self.setting_host_local = DB_API.setting_create(setting_host_local)

    def tearDown(self):
        base.IsolatedUnitTest.tearDown(self)
        #destroy
        DB_API.setting_destroy(self.setting_platform_vcpus.uuid)
        DB_API.setting_destroy(self.setting_host_local.uuid)

    def test_save_setting(self):
        """
        test create a setting and get by uuid
        """
        setting = dict({"uuid": "abc",
                        "enable": True,
                        "deleted": False,
                        "level": models.USER_LEVEL,
                        "type": "vcpus",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        setting = DB_API.setting_create(setting)
        # UUID should has no effect.
        self.assertNotEqual(setting.uuid, "abc")
        self.assertEqual(setting.enable, True)
        self.assertEqual(setting.deleted, False)
        self.assertEqual(setting.level, models.USER_LEVEL)
        self.assertEqual(setting.type, "vcpus")
        self.assertEqual(setting.capacity, 10)
        self.assertEqual(setting.threshold, 80.0)
        self.assertEqual(setting.alarm_title, "test alarm title.")
        self.assertEqual(setting.alarm_content, "test alarm content.")

        #destroy
        DB_API.setting_destroy(setting.uuid)

        self.assertRaises(exception.NotFound,
                          DB_API.setting_get_by_lever_type,
                          models.USER_LEVEL, "vcpus")

    def test_get_setting(self):
        """
        test get setting by uuid
        """
        setting = DB_API.setting_get(self.setting_platform_vcpus.uuid)
        # UUID should has no effect.
        self.assertNotEqual(setting.uuid, "abc")
        self.assertEqual(setting.enable, True)
        self.assertEqual(setting.deleted, False)
        self.assertEqual(setting.level, models.PLATFORM_LEVEL)
        self.assertEqual(setting.type, "vcpus")
        self.assertEqual(setting.capacity, 10)
        self.assertEqual(setting.threshold, 80.0)
        self.assertEqual(setting.alarm_title, "test alarm title.")
        self.assertEqual(setting.alarm_content, "test alarm content.")

    def test_get_by_level_type(self):
        """
        test get setting by level and type pair
        """
        setting = DB_API.setting_get_by_lever_type(models.PLATFORM_LEVEL,
                                                   "vcpus")
        # UUID should has no effect.
        self.assertNotEqual(setting.uuid, "abc")
        self.assertEqual(setting.enable, True)
        self.assertEqual(setting.deleted, False)
        self.assertEqual(setting.level, models.PLATFORM_LEVEL)
        self.assertEqual(setting.type, "vcpus")
        self.assertEqual(setting.capacity, 10)
        self.assertEqual(setting.threshold, 80.0)
        self.assertEqual(setting.alarm_title, "test alarm title.")
        self.assertEqual(setting.alarm_content, "test alarm content.")

    def test_get_all_settings(self):
        """
        test list all settings
        """
        settings = DB_API.setting_get_all(filters={"deleted": False})
        # default ordered by created_at descend.
        self.assertEqual(len(settings), 2)
        self.assertSettingEqual(settings[0], self.setting_host_local)
        self.assertSettingEqual(settings[1], self.setting_platform_vcpus)

    def test_update_setting(self):
        """
        test update setting values
        """
        setting = dict({"level": models.PLATFORM_LEVEL,
                        "type": "vcpus-to-update",
                        "enable": True,
                        "deleted": False
                        })
        setting_ref = DB_API.setting_create(setting)
        self.assertEqual(setting_ref.level, models.PLATFORM_LEVEL)
        self.assertEqual(setting_ref.type, "vcpus-to-update")

        values = {
                  "level": models.USER_LEVEL,
                  "type": "memory-mb"
                  }
        new_setting_ref = DB_API.setting_update(setting_ref.uuid, values)
        self.assertEqual(new_setting_ref.uuid, setting_ref.uuid)
        self.assertEqual(new_setting_ref.level, models.USER_LEVEL)
        self.assertEqual(new_setting_ref.type, "memory-mb")

        DB_API.setting_destroy(setting_ref.uuid)

    def test_destroy_setting(self):
        """
        test destroy specify setting
        """
        setting = dict({"level": models.USER_LEVEL,
                        "type": "vcpus",
                        "enable": True,
                        "deleted": False
                        })
        setting_ref = DB_API.setting_create(setting)

        DB_API.setting_destroy(setting_ref.uuid)
        self.assertRaises(exception.NotFound, DB_API.setting_get,
                          setting_ref.uuid)

    def assertSettingEqual(self, first, second):
        if type(first) is not type(second):
            raise self.failureException("%(first) and %(second) "
                                        "is not same type." % locals())
        self.assertEqual(first.uuid, second.uuid)
        self.assertEqual(first.enable, second.enable)
        self.assertEqual(first.deleted, second.deleted)
        self.assertEqual(first.level, second.level)
        self.assertEqual(first.type, second.type)
        self.assertEqual(first.capacity, second.capacity)
        self.assertEqual(first.threshold, second.threshold)
        self.assertEqual(first.alarm_title, second.alarm_title)
        self.assertEqual(first.alarm_content, second.alarm_content)


class SqlSettingExceptionTest(base.IsolatedUnitTest):
    """
    test sql operation that may cause exception.
    """

    def setUp(self):
        base.IsolatedUnitTest.setUp(self)
        DB_API.configure_db()

    def test_save_same_level_type(self):
        setting = dict({"level": models.PLATFORM_LEVEL,
                        "type": "vcpus",
                        "enable": True,
                        "deleted": False
                        })
        setting_ref = DB_API.setting_create(setting)
        self.assertRaises(exception.Duplicate, DB_API.setting_create, setting)
        #destroy
        DB_API.setting_destroy(setting_ref.uuid)

    def test_update_to_same(self):
        """
        test update setting level and type to values of exist one.
        """
        setting1 = dict({"level": models.PLATFORM_LEVEL,
                        "type": "vcpus-to-compare",
                        "enable": True,
                        "deleted": False
                        })
        setting2 = dict({"level": models.USER_LEVEL,
                        "type": "vcpus-to-modify",
                        "enable": True,
                        "deleted": False
                        })
        setting1_ref = DB_API.setting_create(setting1)
        setting2_ref = DB_API.setting_create(setting2)
        values = {
                  "level": models.PLATFORM_LEVEL,
                  "type": "vcpus-to-compare"
                  }
        self.assertRaises(exception.Duplicate, DB_API.setting_update,
                          setting2_ref.uuid, values)

        DB_API.setting_destroy(setting1_ref.uuid)
        DB_API.setting_destroy(setting2_ref.uuid)

    def test_not_exist(self):
        uuid = "not-exist-uuid"
        self.assertRaises(exception.NotFound, DB_API.setting_get, uuid)

        self.assertRaises(exception.NotFound, DB_API.setting_destroy, uuid)

        self.assertRaises(exception.NotFound, DB_API.setting_update, uuid, {})

        level = models.PLATFORM_LEVEL
        setting_type = "not-exist-setting_type"
        self.assertRaises(exception.NotFound, DB_API.setting_get_by_lever_type,
                          level, setting_type)


class SqlAlarmTest(base.IsolatedUnitTest):

    def setUp(self):
        base.IsolatedUnitTest.setUp(self)
        DB_API.configure_db()
        # create settings
        setting_platform_vcpus = dict({"enable": True,
                        "deleted": False,
                        "level": models.PLATFORM_LEVEL,
                        "type": "vcpus",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        setting_host_local = dict({"enable": True,
                        "deleted": False,
                        "level": models.HOST_LEVEL,
                        "type": "local_gb",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        self.setting_platform_vcpus = DB_API.setting_create(
                                                    setting_platform_vcpus)
        self.setting_host_local = DB_API.setting_create(setting_host_local)

        alarm_platform_vcpus = dict({
                        "settings_uuid": self.setting_platform_vcpus.uuid,
                        "usage": 10})
        alarm_host_local = dict({
                        "settings_uuid": self.setting_host_local.uuid,
                        "usage": 10})
        self.alarm_platform_vcpus = DB_API.alarming_create(
                                                    alarm_platform_vcpus)
        self.alarm_host_local = DB_API.alarming_create(alarm_host_local)

    def tearDown(self):
        base.IsolatedUnitTest.tearDown(self)
        #destroy
        DB_API.alarmings_clear()

        DB_API.setting_destroy(self.setting_platform_vcpus.uuid)
        DB_API.setting_destroy(self.setting_host_local.uuid)

    def test_alarm_create(self):
        """
        test to create a same alarm.
        """
        alarm_platform_vcpus = dict({
                        "settings_uuid": self.setting_platform_vcpus.uuid,
                        "usage": 10})
        alarm_platform_vcpus_ref = DB_API.alarming_create(alarm_platform_vcpus)
        self.assertEqual(alarm_platform_vcpus_ref.settings_uuid,
                         self.setting_platform_vcpus.uuid)
        self.assertEqual(alarm_platform_vcpus_ref.usage, 10)
        self.assertEqual(alarm_platform_vcpus_ref.done, False)
        self.assertEqual(alarm_platform_vcpus_ref.readed, False)
        self.assertEqual(alarm_platform_vcpus_ref.read_user_id, None)
        DB_API.alarming_delete(alarm_platform_vcpus_ref.id)

    def test_alarm_get(self):
        """
        test to get alarm by id.
        """
        alarm_platform_vcpus_ref = \
                    DB_API.alarming_get(self.alarm_platform_vcpus.id)
        self.assertEqual(alarm_platform_vcpus_ref.settings_uuid,
                         self.setting_platform_vcpus.uuid)
        self.assertEqual(alarm_platform_vcpus_ref.usage, 10)
        self.assertEqual(alarm_platform_vcpus_ref.done, False)
        self.assertEqual(alarm_platform_vcpus_ref.readed, False)
        self.assertEqual(alarm_platform_vcpus_ref.read_user_id, None)

    def test_alarm_get_all(self):
        """
        test to get all alarms
        """
        alarms = DB_API.alarming_get_all(filters={"deleted": False})
        self.assertEqual(len(alarms), 2)
        self.assertAlarmEqual(alarms[0], self.alarm_host_local)
        self.assertAlarmEqual(alarms[1], self.alarm_platform_vcpus)

    def test_alarm_update(self):
        """
        test update a updatable attribute
        """
        values = {
                  "done": True,
                  "readed": True,
                  "read_user_id": "test"
                  }
        DB_API.alarming_update(self.alarm_host_local.id, values)
        new_alarm_ref = DB_API.alarming_get(self.alarm_host_local.id)
        self.assertEqual(new_alarm_ref.done, True)
        self.assertEqual(new_alarm_ref.readed, True)
        self.assertEqual(new_alarm_ref.read_user_id, "test")

    def test_alarm_delete(self):
        alarm_platform_vcpus = dict({
                        "settings_uuid": self.setting_platform_vcpus.uuid,
                        "usage": 10})
        alarm_platform_vcpus_ref = DB_API.alarming_create(alarm_platform_vcpus)
        self.assertEqual(alarm_platform_vcpus_ref.deleted, False)
        DB_API.alarming_delete(alarm_platform_vcpus_ref.id)
        self.assertRaises(exception.NotFound, DB_API.alarming_get,
                          alarm_platform_vcpus_ref.id)

    def test_alarm_clear(self):
        alarms = DB_API.alarming_get_all(filters={"deleted": False})
        self.assertEqual(len(alarms), 2)

        DB_API.alarmings_clear()
        alarms = DB_API.alarming_get_all(filters={"deleted": False})
        self.assertEqual(len(alarms), 0)

    def assertAlarmEqual(self, first, second):
        if type(first) is not type(second):
            raise self.failureException("%(first) and %(second) "
                                        "is not same type." % locals())
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.settings_uuid, second.settings_uuid)
        self.assertEqual(first.deleted, second.deleted)
        self.assertEqual(first.usage, second.usage)
        self.assertEqual(first.done, second.done)
        self.assertEqual(first.readed, second.readed)
        self.assertEqual(first.read_user_id, second.read_user_id)


class SqlAlarmExceptionTest(base.IsolatedUnitTest):

    def setUp(self):
        base.IsolatedUnitTest.setUp(self)
        DB_API.configure_db()
        # create settings
        setting_platform_vcpus = dict({"enable": True,
                        "deleted": False,
                        "level": models.PLATFORM_LEVEL,
                        "type": "vcpus",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        setting_host_local = dict({"enable": True,
                        "deleted": False,
                        "level": models.HOST_LEVEL,
                        "type": "local_gb",
                        "capacity": 10,
                        "threshold": 80.0,
                        "alarm_title": "test alarm title.",
                        "alarm_content": "test alarm content."})
        self.setting_platform_vcpus = DB_API.setting_create(
                                                    setting_platform_vcpus)
        self.setting_host_local = DB_API.setting_create(setting_host_local)

        alarm_platform_vcpus = dict({
                        "settings_uuid": self.setting_platform_vcpus.uuid,
                        "usage": 10})
        alarm_host_local = dict({
                        "settings_uuid": self.setting_host_local.uuid,
                        "usage": 10})
        self.alarm_platform_vcpus = DB_API.alarming_create(
                                                    alarm_platform_vcpus)
        self.alarm_host_local = DB_API.alarming_create(alarm_host_local)

    def tearDown(self):
        base.IsolatedUnitTest.tearDown(self)
        #destroy
        DB_API.alarming_delete(self.alarm_platform_vcpus.id)
        DB_API.alarming_delete(self.alarm_host_local.id)

        DB_API.setting_destroy(self.setting_platform_vcpus.uuid)
        DB_API.setting_destroy(self.setting_host_local.uuid)

    def test_not_exist(self):
        """
        test to get, update or delete not exist.
        """
        id = "not-exist-alarm-id"
        self.assertRaises(exception.NotFound, DB_API.alarming_get, id)

        self.assertRaises(exception.NotFound, DB_API.alarming_update, id, {})

        self.assertRaises(exception.NotFound, DB_API.alarming_delete, id)

    def test_update_not_updatable_attr(self):
        """
        test to update attributes which should not update.
        """
        usage_to_update = 0
        self.assertRaises(exception.UnableUpdateValue, DB_API.alarming_update,
                          self.alarm_platform_vcpus.id,
                          {"usage": usage_to_update})

        settings_uuid_to_update = ""
        self.assertRaises(exception.UnableUpdateValue, DB_API.alarming_update,
                          self.alarm_platform_vcpus.id,
                          {"settings_uuid": settings_uuid_to_update})

        id_to_update = 0
        self.assertRaises(exception.UnableUpdateValue, DB_API.alarming_update,
                          self.alarm_platform_vcpus.id,
                          {"id": id_to_update})
