from hawkular.client import ApiObject, HawkularBaseClient
from hawkular.alerts.triggers import AlertsTriggerClient

class Status(ApiObject):
    __slots__ = [
        'status', 'implementation_version', 'built_from_git_sha1', 'distributed', 'members'
    ]

    def isup(self):
        return self.status == 'STARTED'

    def isdistributed(self):
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

    # def triggers(self):
    #     """
    #     Returns triggers methods
    #     """
    #     return AlertsTriggerClient(self)

    def status(self):
        orig_dict = self._get(self._service_url('status'))
        orig_dict['implementation_version'] = orig_dict.pop('Implementation-Version')
        orig_dict['built_from_git_sha1'] = orig_dict.pop('Built-From-Git-SHA1')
        return Status(orig_dict)
