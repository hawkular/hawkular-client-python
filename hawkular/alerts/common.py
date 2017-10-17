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
from hawkular.client import ApiObject, HawkularBaseClient
from hawkular.alerts.triggers import AlertsTriggerClient

class Status(ApiObject):
    __slots__ = [
        'status', 'implementation_version', 'built_from_git_sha1', 'distributed', 'members'
    ]

    def isup(self):
        """
        Returns if the alerting service is ready to accept requests.

        :return: bool True if available
        """
        return self.status == 'STARTED'

    def isdistributed(self):
        """
        Is the Alerting Service running in distributed mode or standalone.

        :return: bool True if distributed
        """
        return self.distributed == 'true'

class HawkularAlertsClient(HawkularBaseClient):

    def __init__(self, **opts):
        """
        Available parameters:

                 tenant_id,
                 host='localhost',
                 port=8080,
                 path=None,
                 scheme='http',
                 cafile=None,
                 context=None,
                 token=None,
                 username=None,
                 password=None,
                 auto_set_legacy_api=True,
                 authtoken=None
        """
        prop_defaults = {
            "tenant_id": 'hawkular',
            "host": 'localhost',
            "port": 8080,
            "scheme": 'http',
            "path": None,
            "cafile": None,
            "context": None,
            "token": None,
            "username": None,
            "password": None,
            "authtoken": None,
        }

        for (prop, default) in prop_defaults.items():
            setattr(self, prop, opts.get(prop, default))

        super(HawkularAlertsClient, self)._setup_path()

        self.triggers = AlertsTriggerClient(self)

    def status(self):
        """
        Get the status of Alerting Service

        :return: Status object
        """
        orig_dict = self._get(self._service_url('status'))
        orig_dict['implementation_version'] = orig_dict.pop('Implementation-Version')
        orig_dict['built_from_git_sha1'] = orig_dict.pop('Built-From-Git-SHA1')
        return Status(orig_dict)
