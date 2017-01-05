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
from hawkular.client import ApiOject, HawkularBaseClient

class Trigger(ApiOject):
    __slots__ = [
        'id', 'name', 'description', 'type', 'event_type', 'event_category',
        'event_text', 'event_category', 'event_text', 'severity', 'context',
        'tags', 'actions', 'auto_disable', 'auto_enable', 'auto_resolve',
        'auto_resolve_alerts', 'auto_resolve_match', 'data_id_map', 'member_of',
        'enabled', 'firing_match', 'source'
    ]


class Condition(ApiOject):
    __slots__ = [
        'trigger_id', 'trigger_mode', 'type', 'condition_set_size',
        'condition_set_index', 'condition_id', 'context', 'data_id',
        'operator', 'data2_id', 'data2_multiplier', 'pattern', 'ignore_case',
        'threshold', 'operator_low', 'operator_high', 'threshold_low', 'threshold_high',
        'in_range', 'alerter_id', 'expression', 'direction', 'period', 'interval'
    ]


class Dampening(ApiOject):
    __slots__ = [
        'trigger_id', 'trigger_mode', 'type', 'eval_true_setting',
        'eval_total_setting', 'eval_time_setting', 'dampening_id'
    ]


class FullTrigger(ApiOject):
    defaults = {
        'conditions': [],
        'dampenings': []
    }
    __slots__ = [
        'trigger', 'dampenings', 'conditions'
    ]

    def __init__(self, dictionary=dict()):
        udict = FullTrigger.transform_dict_to_underscore(dictionary)
        self.trigger = Trigger(udict.get('trigger'))
        self.dampenings = Dampening.list_to_object_list(udict.get('dampenings'))
        self.conditions = Condition.list_to_object_list(udict.get('conditions'))


class GroupMemberInfo(ApiOject):
    __slots__ = [
        'group_id', 'member_id', 'member_name', 'member_description', 'member_context',
        'member_tags', 'data_id_map'
    ]


class GroupConditionsInfo(ApiOject):
    __slots__ = [
        'conditions', 'data_id_member_map'
    ]

    def __init__(self, dictionary=dict()):
        ApiOject.__init__(self, dictionary)
        udict = self.transform_dict_to_underscore(dictionary)
        self.conditions = Condition.list_to_object_list(udict.get('conditions'))

    def addCondition(self, c):
        self.conditions.append(c)


class TriggerType:
    STANDARD = 'STANDARD'
    GROUP = 'GROUP'
    DATA_DRIVEN_GROUP = 'DATA_DRIVEN_GROUP'
    MEMBER = 'MEMBER'
    ORPHAN = 'ORPHAN'


class TriggerMode:
    FIRING = 'FIRING'
    AUTORESOLVE = 'AUTORESOLVE'


class DampeningType:
    STRICT = 'STRICT'
    RELAXED_COUNT = 'RELAXED_COUNT'
    RELAXED_TIME = 'RELAXED_TIME'
    STRICT_TIME = 'STRICT_TIME'
    STRICT_TIMEOUT = 'STRICT_TIMEOUT'


class ConditionType:
    AVAILABILITY = 'AVAILABILITY'
    COMPARE = 'COMPARE'
    STRING = 'STRING'
    THRESHOLD = 'THRESHOLD'
    RANGE = 'RANGE'
    EXTERNAL = 'EXTERNAL'
    EVENT = 'EVENT'
    RATE = 'RATE'
    MISSING = 'MISSING'


class Operator:
    LT = 'LT'
    GT = 'GT'
    LTE = 'LTE'
    GTE = 'GTE'


class Severity:
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class HawkularAlertsClient(HawkularBaseClient):
    def list_triggers(self, ids=[], tags=[]):
        ids = ','.join(ids)
        tags = ','.join(tags)
        url = self._service_url('triggers', {'tags': tags, 'ids': ids})
        triggers_dict = self._get(url)
        return Trigger.list_to_object_list(triggers_dict)

    def create_trigger(self, trigger):
        data = self._serialize_object(trigger)
        if isinstance(trigger, FullTrigger):
            returned_dict = self._post(self._service_url(['triggers', 'trigger']), data)
            return FullTrigger(returned_dict)
        else:
            returned_dict = self._post(self._service_url('triggers'), data)
            return Trigger(returned_dict)

    def get_trigger(self, trigger_id, full=False):
        if full:
            returned_dict = self._get(self._service_url(['triggers', 'trigger', trigger_id]))
            return FullTrigger(returned_dict)
        else:
            returned_dict = self._get(self._service_url(['triggers', trigger_id]))
            return Trigger(returned_dict)

    def create_group_trigger(self, trigger):
        data = self._serialize_object(trigger)
        return Trigger(self._post(self._service_url(['triggers', 'groups']), data))

    def get_group_members(self, group_id):
        """
        Find all group member trigger definitions
        :param group_id: group trigger id
        :return: list of asociated group members as trigger objects
        """
        url = self._service_url(['triggers', 'groups', group_id, 'members'])
        return Trigger.list_to_object_list(self._get(url))

    def update_group_trigger(self, group_id, trigger):
        """
        :param group_id: group trigger id to be updated
        :param trigger: Trigger object, the group trigger to be updated
        """
        data = self._serialize_object(trigger)
        self._put(self._service_url(['triggers', 'groups', group_id]), data, parse_json=False)

    def delete_group_trigger(self, group_id, keep_non_orphans=False, keep_orphans=False):
        """
        Delete a group trigger
        :param group_id: ID of the group trigger to delete
        :param keep_non_orphans: if True converts the non-orphan member triggers to standard triggers
        :param keep_orphans: if True converts the orphan member triggers to standard triggers
        """
        params = {'keepNonOrphans': str(keep_non_orphans).lower(), 'keepOrphans': str(keep_orphans).lower()}
        self._delete(self._service_url(['triggers', 'groups', group_id], params=params))

    def create_group_member(self, member):
        data = self._serialize_object(member)
        return Trigger(self._post(self._service_url(['triggers', 'groups', 'members']), data))

    def get_trigger_conditions(self, trigger_id):
        """
        Get all conditions for a specific trigger
        :param trigger_id: Trigger definition id to be retrieved
        :return: list of condition objects
        """
        response = self._get(self._service_url(['triggers', trigger_id, 'conditions']))
        return  Condition.list_to_object_list(response)

    def create_group_conditions(self, group_id, trigger_mode, conditions):
        data = self._serialize_object(conditions)
        url = self._service_url(['triggers', 'groups', group_id, 'conditions', trigger_mode])
        response = self._put(url, data)
        return Condition.list_to_object_list(response)

    def list_dampenings(self, trigger_id):
        url = self._service_url(['triggers', trigger_id, 'dampenings'])
        data = self._get(url)
        return Dampening.list_to_object_list(data)
