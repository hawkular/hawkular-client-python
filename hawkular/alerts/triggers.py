"""
   Copyright 2015-2017 Red Hat, Inc. and/or its affiliates
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
from hawkular.client import ApiObject

class Trigger(ApiObject):
    __slots__ = [
        'id', 'name', 'description', 'type', 'event_type', 'event_category',
        'event_text', 'event_category', 'event_text', 'severity', 'context',
        'tags', 'actions', 'auto_disable', 'auto_enable', 'auto_resolve',
        'auto_resolve_alerts', 'auto_resolve_match', 'data_id_map', 'member_of',
        'enabled', 'firing_match', 'source'
    ]

class Condition(ApiObject):
    __slots__ = [
        'trigger_id', 'trigger_mode', 'type', 'condition_set_size',
        'condition_set_index', 'condition_id', 'context', 'data_id',
        'operator', 'data2_id', 'data2_multiplier', 'pattern', 'ignore_case',
        'threshold', 'operator_low', 'operator_high', 'threshold_low', 'threshold_high',
        'in_range', 'alerter_id', 'expression', 'direction', 'period', 'interval'
    ]

class Dampening(ApiObject):
    __slots__ = [
        'trigger_id', 'trigger_mode', 'type', 'eval_true_setting',
        'eval_total_setting', 'eval_time_setting', 'dampening_id'
    ]

class FullTrigger(ApiObject):
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

class GroupMemberInfo(ApiObject):
    __slots__ = [
        'group_id', 'member_id', 'member_name', 'member_description', 'member_context',
        'member_tags', 'data_id_map'
    ]

class GroupConditionsInfo(ApiObject):
    __slots__ = [
        'conditions', 'data_id_member_map'
    ]

    def __init__(self, dictionary=dict()):
        ApiObject.__init__(self, dictionary)
        udict = self.transform_dict_to_underscore(dictionary)
        self.conditions = Condition.list_to_object_list(udict.get('conditions'))

    def addCondition(self, c):
        self.conditions.append(c)

class UnorphanMemberInfo(ApiObject):
    __slots__ = [
        'member_context', 'member_tags', 'data_id_map'
    ]

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

class AlertsTriggerClient(object):

    def __init__(self, alerts_client):
        self.__client = alerts_client
        pass

    def __getattr__(self, name):
        return getattr(self.__client, name)

    def get(self, tags=[], trigger_ids=[]):
        """
        Get triggers with optional filtering. Querying without parameters returns all the trigger definitions.

        :param tags: Fetch triggers with matching tags only. Use * to match all values.
        :param trigger_ids: List of triggerIds to fetch
        """
        params = {}
        if len(tags) > 0:
            params['tags'] = ','.join(tags)

        if len(trigger_ids) > 0:
            params['triggerIds'] = ','.join(trigger_ids)

        url = self._service_url('triggers', params=params)
        triggers_dict = self._get(url)
        return Trigger.list_to_object_list(triggers_dict)

    def create(self, trigger):
        """
        Create a new trigger.

        :param trigger: FullTrigger or Trigger class to be created
        :return: The created trigger
        """
        data = self._serialize_object(trigger)
        if isinstance(trigger, FullTrigger):
            returned_dict = self._post(self._service_url(['triggers', 'trigger']), data)
            return FullTrigger(returned_dict)
        else:
            returned_dict = self._post(self._service_url('triggers'), data)
            return Trigger(returned_dict)

    def update(self, trigger_id, full_trigger):
        """
        Update an existing full trigger.

        :param full_trigger: FullTrigger with conditions, dampenings and triggers
        :type full_trigger: FullTrigger
        :return: Updated FullTrigger definition
        """
        data = self._serialize_object(full_trigger)
        rdict = self._put(self._service_url(['triggers', 'trigger', trigger_id]), data)
        return FullTrigger(rdict)

    def delete(self, trigger_id):
        """
        Delete an existing standard or group member trigger.

        This can not be used to delete a group trigger definition.

        :param trigger_id: Trigger definition id to be deleted.
        """
        self._delete(self._service_url(['triggers', trigger_id]))

    def single(self, trigger_id, full=False):
        """
        Get an existing (full) trigger definition.

        :param trigger_id: Trigger definition id to be retrieved.
        :param full: Fetch the full definition, default is False.
        :return: Trigger of FullTrigger depending on the full parameter value.
        """
        if full:
            returned_dict = self._get(self._service_url(['triggers', 'trigger', trigger_id]))
            return FullTrigger(returned_dict)
        else:
            returned_dict = self._get(self._service_url(['triggers', trigger_id]))
            return Trigger(returned_dict)

    def create_group(self, trigger):
        """
        Create a new group trigger.

        :param trigger: Group member trigger to be created
        :return: The created group Trigger
        """
        data = self._serialize_object(trigger)
        return Trigger(self._post(self._service_url(['triggers', 'groups']), data))

    def group_members(self, group_id, include_orphans=False):
        """
        Find all group member trigger definitions

        :param group_id: group trigger id
        :param include_orphans: If True, include orphan members
        :return: list of asociated group members as trigger objects
        """
        params = {'includeOrphans': str(include_orphans).lower()}
        url = self._service_url(['triggers', 'groups', group_id, 'members'], params=params)
        return Trigger.list_to_object_list(self._get(url))

    def update_group(self, group_id, trigger):
        """
        Update an existing group trigger definition and its member definitions.

        :param group_id: Group trigger id to be updated
        :param trigger: Trigger object, the group trigger to be updated
        """
        data = self._serialize_object(trigger)
        self._put(self._service_url(['triggers', 'groups', group_id]), data, parse_json=False)

    def delete_group(self, group_id, keep_non_orphans=False, keep_orphans=False):
        """
        Delete a group trigger

        :param group_id: ID of the group trigger to delete
        :param keep_non_orphans: if True converts the non-orphan member triggers to standard triggers
        :param keep_orphans: if True converts the orphan member triggers to standard triggers
        """
        params = {'keepNonOrphans': str(keep_non_orphans).lower(), 'keepOrphans': str(keep_orphans).lower()}
        self._delete(self._service_url(['triggers', 'groups', group_id], params=params))

    def create_group_member(self, member):
        """
        Create a new member trigger for a parent trigger.

        :param member: Group member trigger to be created
        :type member: GroupMemberInfo
        :return: A member Trigger object
        """
        data = self._serialize_object(member)
        return Trigger(self._post(self._service_url(['triggers', 'groups', 'members']), data))

    def set_group_conditions(self, group_id, conditions, trigger_mode=None):
        """
        Set the group conditions.

        This replaces any existing conditions on the group and member conditions for all trigger modes.

        :param group_id: Group to be updated
        :param conditions: New conditions to replace old ones
        :param trigger_mode: Optional TriggerMode used
        :type conditions: GroupConditionsInfo
        :type trigger_mode: TriggerMode
        :return: The new Group conditions
        """
        data = self._serialize_object(conditions)

        if trigger_mode is not None:
            url = self._service_url(['triggers', 'groups', group_id, 'conditions', trigger_mode])
        else:
            url = self._service_url(['triggers', 'groups', group_id, 'conditions'])

        response = self._put(url, data)
        return Condition.list_to_object_list(response)

    def set_conditions(self, trigger_id, conditions, trigger_mode=None):
        """
        Set the conditions for the trigger.

        This sets the conditions for all trigger modes, replacing existing conditions for all trigger modes.

        :param trigger_id: The relevant Trigger definition id
        :param trigger_mode: Optional Trigger mode
        :param conditions: Collection of Conditions to set.
        :type trigger_mode: TriggerMode
        :type conditions: List of Condition
        :return: The new conditions.
        """
        data = self._serialize_object(conditions)
        if trigger_mode is not None:
            url = self._service_url(['triggers', trigger_id, 'conditions', trigger_mode])
        else:
            url = self._service_url(['triggers', trigger_id, 'conditions'])

        response = self._put(url, data)
        return Condition.list_to_object_list(response)

    def conditions(self, trigger_id):
        """
        Get all conditions for a specific trigger.

        :param trigger_id: Trigger definition id to be retrieved
        :return: list of condition objects
        """
        response = self._get(self._service_url(['triggers', trigger_id, 'conditions']))
        return  Condition.list_to_object_list(response)

    def dampenings(self, trigger_id, trigger_mode=None):
        """
        Get all Dampenings for a Trigger (1 Dampening per mode).

        :param trigger_id: Trigger definition id to be retrieved.
        :param trigger_mode: Optional TriggerMode which is only fetched
        :type trigger_mode: TriggerMode
        :return: List of Dampening objects
        """
        if trigger_mode is not None:
            url = self._service_url(['triggers', trigger_id, 'dampenings', 'mode', trigger_mode])
        else:
            url = self._service_url(['triggers', trigger_id, 'dampenings'])

        data = self._get(url)
        return Dampening.list_to_object_list(data)

    def create_dampening(self, trigger_id, dampening):
        """
        Create a new dampening.

        :param trigger_id: TriggerId definition attached to the dampening
        :param dampening: Dampening definition to be created.
        :type dampening: Dampening
        :return: Created dampening
        """
        data = self._serialize_object(dampening)
        url = self._service_url(['triggers', trigger_id, 'dampenings'])
        return Dampening(self._post(url, data))

    def delete_dampening(self, trigger_id, dampening_id):
        """
        Delete an existing dampening definition.

        :param trigger_id: Trigger definition id for deletion.
        :param dampening_id: Dampening definition id to be deleted.
        """
        self._delete(self._service_url(['triggers', trigger_id, 'dampenings', dampening_id]))

    def update_dampening(self, trigger_id, dampening_id):
        """
        Update an existing dampening definition.

        Note that the trigger mode can not be changed using this method.
        :param trigger_id: Trigger definition id targeted for update.
        :param dampening_id: Dampening definition id to be updated.
        :return: Updated Dampening
        """
        data = self._serialize_object(dampening)
        url = self._service_url(['triggers', trigger_id, 'dampenings', dampening_id])
        return Dampening(self._put(url, data))

    def create_group_dampening(self, group_id, dampening):
        """
        Create a new group dampening

        :param group_id: Group Trigger id attached to dampening
        :param dampening: Dampening definition to be created.
        :type dampening: Dampening
        :return: Group Dampening created
        """
        data = self._serialize_object(dampening)
        url = self._service_url(['triggers', 'groups', group_id, 'dampenings'])
        return Dampening(self._post(url, data))

    def update_group_dampening(self, group_id, dampening_id, dampening):
        """
        Update an existing group dampening

        :param group_id: Group Trigger id attached to dampening
        :param dampening_id: id of the dampening to be updated
        :return: Group Dampening created
        """
        data = self._serialize_object(dampening)
        url = self._service_url(['triggers', 'groups', group_id, 'dampenings', dampening_id])
        return Dampening(self._put(url, data))

    def delete_group_dampening(self, group_id, dampening_id):
        """
        Delete an existing group dampening

        :param group_id: Group Trigger id to be retrieved
        :param dampening_id: id of the Dampening to be deleted
        """
        self._delete(self._service_url(['triggers', 'groups', group_id, 'dampenings', dampening_id]))

    def set_group_member_orphan(self, member_id):
        """
        Make a non-orphan member trigger into an orphan.

        :param member_id: Member Trigger id to be made an orphan.
        """
        self._put(self._service_url(['triggers', 'groups', 'members', member_id, 'orphan']), data=None, parse_json=False)

    def set_group_member_unorphan(self, member_id, unorphan_info):
        """
        Make an orphan member trigger into an group trigger.

        :param member_id: Orphan Member Trigger id to be assigned into a group trigger
        :param unorphan_info: Only context and dataIdMap are used when changing back to a non-orphan.
        :type unorphan_info: UnorphanMemberInfo
        :return: Trigger for the group
        """
        data = self._serialize_object(unorphan_info)
        data = self._service_url(['triggers', 'groups', 'members', member_id, 'unorphan'])
        return Trigger(self._put(url, data))

    def enable(self, trigger_ids=[]):
        """
        Enable triggers.

        :param trigger_ids: List of trigger definition ids to enable
        """
        trigger_ids = ','.join(trigger_ids)
        url = self._service_url(['triggers', 'enabled'], params={'triggerIds': trigger_ids, 'enabled': 'true'})
        self._put(url, data=None, parse_json=False)

    def disable(self, trigger_ids=[]):
        """
        Disable triggers.

        :param trigger_ids: List of trigger definition ids to disable
        """
        trigger_ids = ','.join(trigger_ids)
        url = self._service_url(['triggers', 'enabled'], params={'triggerIds': trigger_ids, 'enabled': 'false'})
        self._put(url, data=None, parse_json=False)

    def enable_group(self, trigger_ids=[]):
        """
        Enable group triggers.

        :param trigger_ids: List of group trigger definition ids to enable
        """
        trigger_ids = ','.join(trigger_ids)
        url = self._service_url(['triggers', 'groups', 'enabled'], params={'triggerIds': trigger_ids, 'enabled': 'true'})
        self._put(url, data=None, parse_json=False)

    def disable_group(self, trigger_ids=[]):
        """
        Disable group triggers.

        :param trigger_ids: List of group trigger definition ids to disable
        """
        trigger_ids = ','.join(trigger_ids)
        url = self._service_url(['triggers', 'groups', 'enabled'], params={'triggerIds': trigger_ids, 'enabled': 'false'})
        self._put(url, data=None, parse_json=False)
