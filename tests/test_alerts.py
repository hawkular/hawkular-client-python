"""
   Copyright 2015-2016 Red Hat, Inc. and/or its affiliates
   and other contributors.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from __future__ import unicode_literals

import unittest
import uuid
from hawkular.alerts import *
import os
from tests import base

try:
    # Python 3
    from urllib.error import HTTPError
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import HTTPError


class TestAlertsFunctionsBase(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.test_tenant = str(uuid.uuid4())
        self.client = HawkularAlertsClient(tenant_id=self.test_tenant,
                                           port=8080)


@unittest.skipIf(base.version != 'latest' and base.major_version == 0 and base.minor_version <= 15,
                 'Not supported in ' + base.version + ' version')
class AlertsTestCase(TestAlertsFunctionsBase):
    def test_trigger_creation(self):
        trigger = Trigger()
        trigger.id = 'id_1'
        trigger.name = 'test_trigger'
        created_trigger = self.client.create_trigger(trigger)
        self.assertEqual(trigger.id, created_trigger.id)
        triggers = self.client.list_triggers()
        self.assertEqual(1, len(triggers))
        self.assertEqual(triggers[0].id, trigger.id)

    def test_full_trigger_creation(self):
        trigger = Trigger()
        trigger.id = 'id_1'
        trigger.name = 'test_trigger'
        full_trigger = FullTrigger()
        full_trigger.trigger = trigger

        # Creating dampening using object attributes.

        dampening1 = Dampening()
        dampening1.dampening_id = 'damp_1'
        dampening1.trigger_mode = TriggerMode.FIRING
        dampening1.type = DampeningType.STRICT

        # Creating dampening using a hash.

        dampening2 = Dampening({
            'dampening_id': 'damp_2',
            'trigger_mode': TriggerMode.AUTORESOLVE,
            'type': DampeningType.RELAXED_COUNT
        })

        condition1 = Condition()
        condition1.trigger_mode = TriggerMode.AUTORESOLVE
        condition1.type = ConditionType.THRESHOLD
        condition1.data_id = 'did1'
        condition1.threshold = 5
        condition1.operator = Operator.LT

        condition2 = Condition()
        condition2.trigger_mode = TriggerMode.AUTORESOLVE
        condition2.type = ConditionType.THRESHOLD
        condition2.data_id = 'did2'
        condition2.threshold = 5
        condition2.operator = Operator.GT

        condition3 = Condition()
        condition3.trigger_mode = TriggerMode.AUTORESOLVE
        condition3.type = ConditionType.THRESHOLD
        condition3.data_id = 'did3'
        condition3.threshold = 5
        condition3.operator = Operator.GTE

        full_trigger.dampenings.append(dampening1)
        full_trigger.dampenings.append(dampening2)
        full_trigger.conditions = [condition1, condition2, condition3]

        created_trigger = self.client.create_trigger(full_trigger)
        self.assertEqual(trigger.id, created_trigger.trigger.id)

        # Check if the trigger appears on the list.

        triggers = self.client.list_triggers()
        self.assertEqual(1, len(triggers))
        self.assertEqual(triggers[0].id, trigger.id)

        # Check if it is possible to get the full trigger.

        created_full_trigger = self.client.get_trigger('id_1', True)

        self.assertTrue(isinstance(created_full_trigger, FullTrigger))
        self.assertEqual(created_full_trigger.trigger.id, trigger.id)
        self.assertEqual(len(created_full_trigger.dampenings), 2)
        self.assertEqual(len(created_full_trigger.conditions), 3)

        # Check for dampenings.

        dampenings = self.client.list_dampenings('id_1')
        self.assertEqual(2, len(dampenings))
        self.assertEqual(dampenings[0].trigger_id, trigger.id)
        self.assertEqual(dampenings[1].trigger_id, trigger.id)

    def test_create_group_trigger(self):
        trigger = Trigger()
        trigger.id = 'group_trigger_1'
        trigger.name = 'group_trigger_test'
        self.client.create_group_trigger(trigger)
        created_group_trigger = created_full_trigger = self.client.get_trigger('group_trigger_1')
        self.assertEqual(created_group_trigger.id, trigger.id)
        self.assertEqual(created_group_trigger.name, trigger.name)

    def test_delete_group_trigger(self):
        # Create a group trigger
        gt = Trigger()
        gt.id = 'delete_group_trigger'
        gt.name = 'group_trigger_to_delete'
        self.client.create_group_trigger(gt)

        group_count = len(self.client.list_triggers())
        # Delete the created group trigger
        self.client.delete_group_trigger('delete_group_trigger')

        # Compare number of remaining triggers and query the deleted trigger id
        self.assertEqual(len(self.client.list_triggers()), group_count-1)
        with self.assertRaises(HTTPError) as e:
            self.client.get_trigger('delete_group_trigger')
            self.assertEqual(e.getcode(), 404)

    def test_create_groups(self):
        # Create a group trigger
        t = Trigger()
        t.enabled = False
        t.id = 'a-group-trigger'
        t.name = 'A Group Trigger'
        t.severity = Severity.HIGH
        t.description = 'A Group Trigger generated from test'

        # Create a condition
        c = Condition()
        c.trigger_mode = TriggerMode.FIRING
        c.type = ConditionType.THRESHOLD
        c.data_id = 'my-metric-id'
        c.operator = Operator.LT
        c.threshold = 5

        gc = GroupConditionsInfo()
        gc.addCondition(c)

        # Create a member
        m1 = GroupMemberInfo()
        m1.group_id = 'a-group-trigger'
        m1.member_id = 'member1'
        m1.member_name = 'Member One'
        m1.data_id_map = {'my-metric-id': 'my-metric-id-member1'}

        tc = self.client.create_group_trigger(t)
        self.assertEqual(tc.type, TriggerType.GROUP)
        gcc = self.client.create_group_conditions(t.id, TriggerMode.FIRING, gc)
        self.assertEqual(len(gcc), 1)
        t_m1c = self.client.create_group_member(m1)
        self.assertEqual(t_m1c.type, TriggerType.MEMBER)

        # Update group trigger
        t.enabled = True
        t.severity = Severity.MEDIUM

        self.client.update_group_trigger(t.id, t)
        gt = self.client.get_trigger(t.id)
        self.assertEqual(gt.enabled, True)
        self.assertEqual(gt.severity, Severity.MEDIUM)
