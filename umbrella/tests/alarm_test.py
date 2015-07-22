'''
Created on 2012-11-7

@author: hzzhoushaoyu
'''
import unittest
import time

from umbrella.common import local
import umbrella.db
from umbrella.db.sqlalchemy import models
from umbrella.db.sqlalchemy import api
from umbrella.monitor import alarm

from umbrella.tests import base
from umbrella.tests import utils


class AlarmTest(base.IsolatedUnitTest):

    def setUp(self):
        base.IsolatedUnitTest.setUp(self)
        self.config(no_replicate_alarm_seconds=10000,
                    alarm_replicate_usage_changed=True)
        self.stubs.Set(umbrella.db, "get_api", utils.FakeDB.get_api)
        self.alarm_check = alarm.AlarmCheck()
        self.db_api = self.alarm_check.db_api
        self.setting = self.db_api.setting_set(level=models.PLATFORM_LEVEL,
                                setting_type="vcpus",
                                capacity=10,
                                threshold=80.0)

    def tearDown(self):
        base.IsolatedUnitTest.tearDown(self)
        self.db_api.alarming_clear()
        local.dict_store().store_dict = {}

    def test_no_alarm(self):
        """
        check usage that will not cause alarm
        """
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          7)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 0)

    def test_alarm(self):
        """
        check usage that will cause alarm
        """
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 1)
        alarm = alarms.values()[0]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)

    def test_replicate_alarm_same_usage(self):
        """
        test not alarm of replicate same usage in seconds
        """
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 1)
        alarm = alarms.values()[0]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)

    def test_replicate_alarm_changed_usage(self):
        """
        test alarm of replicate while usage changed in seconds
        """
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          10)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 2)
        alarm = alarms.values()[0]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)
        alarm = alarms.values()[1]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)

    def test_no_replicate_alarm_changed_usage(self):
        """
        test no alarm of replicate while usage changed in seconds
        """
        self.config(no_replicate_alarm_seconds=10000,
                    alarm_replicate_usage_changed=False)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          10)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 1)
        alarm = alarms.values()[0]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)

    def test_alarm_out_times(self):
        """
        test alarm again while time outs.
        """
        self.config(no_replicate_alarm_seconds=0.1,
                    alarm_replicate_usage_changed=False)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        time.sleep(0.1)
        self.alarm_check.check_type_usage(models.PLATFORM_LEVEL,
                                          "vcpus",
                                          9)
        alarms = self.db_api.alarming_get_all()
        self.assertEqual(len(alarms), 2)
        alarm = alarms.values()[0]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)
        alarm = alarms.values()[1]
        self.assertEqual(alarm['settings_uuid'], self.setting.uuid)

if __name__ == '__main__':
    unittest.main()
