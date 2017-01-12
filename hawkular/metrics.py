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

import codecs
import time
import collections
import base64
import ssl

try:
    import simplejson as json
except ImportError:
    import json

from hawkular.client import ApiOject, HawkularBaseClient, HawkularMetricsError
from hawkular.client import HawkularMetricsConnectionError, HawkularMetricsStatusError

class MetricType:
    Gauge = 'gauges'
    Availability = 'availability'
    Counter = 'counters'
    String = 'strings'
    Rate = 'rate'
    _Metrics = 'metrics'

    @staticmethod
    def short(metric_type):
        if metric_type is MetricType.Gauge:
            return 'gauge'
        elif metric_type is MetricType.Counter:
            return 'counter'
        elif metric_type is MetricType.String:
            return 'string'
        else:
            return 'availability'

class Availability:
    Down = 'down'
    Up = 'up'
    Unknown = 'unknown'

class HawkularMetricsClient(HawkularBaseClient):
    """
    Internal methods
    """
    @staticmethod
    def _clean_metric_id(metric_id):
        return HawkularBaseClient.quote(metric_id)

    def _get_url(self, metric_type=None):
        if metric_type is None:
            metric_type = MetricType._Metrics

        return self._get_base_url() + '{0}'.format(metric_type)

    def _get_metrics_single_url(self, metric_type, metric_id):
        return self._get_url(metric_type) + '/{0}'.format(self._clean_metric_id(metric_id))

    def _get_metrics_raw_url(self, metrics_url):
        return metrics_url + '/data' if self.legacy_api else metrics_url + '/raw'

    def _get_metrics_stats_url(self, metrics_url):
        return metrics_url + '/data' if self.legacy_api else metrics_url + '/stats'

    def _get_metrics_tags_url(self, metrics_url):
        return metrics_url + '/tags'

    def _get_tenants_url(self):
        return self._get_base_url() + 'tenants'

    def _get_status_url(self):
        return self._get_base_url() + 'status'

    @staticmethod
    def _transform_tags(**tags):
        return ','.join("%s:%s" % (key,val) for (key,val) in tags.items())
        
    def _isfloat(value):
        try:
            float(value)
            return True
        except ValueError:
            return False
        
    """
    External methods
    """    

    def tenant(self, tenant_id):
        self.tenant_id = tenant_id

    """
    Instance methods
    """
    
    def put(self, data):
        """
        Send multiple different metric_ids to the server in a single batch. Metrics can be a mixture
        of types.

        data is a dict or a list of dicts created with create_metric(metric_type, metric_id, datapoints)
        """
        if not isinstance(data, list):
            data = [data]

        r = collections.defaultdict(list)

        for d in data:
            metric_type = d.pop('type', None)
            if metric_type is None:
                raise HawkularMetricsError('Undefined MetricType')
            r[metric_type].append(d)

        # This isn't transactional, but .. ouh well. One can always repost everything.
        for l in r:
            self._post(self._get_metrics_raw_url(self._get_url(l)), r[l],parse_json=False)

    def push(self, metric_type, metric_id, value, timestamp=None):
        """
        Pushes a single metric_id, datapoint combination to the server.

        This method is an assistant method for the put method by removing the need to
        create data structures first.
        """
        item = create_metric(metric_type, metric_id, create_datapoint(value, timestamp))
        self.put(item)

    def query_metric(self, metric_type, metric_id, **query_options):
        """
        Query for metrics from the server. For possible query_options, see the Hawkular-Metrics documentation.
        """
        return self._get(
            self._get_metrics_raw_url(
                self._get_metrics_single_url(metric_type, metric_id)),
            **query_options)

    def query_metric_stats(self, metric_type, metric_id, **query_options):
        return self._get(
            self._get_metrics_stats_url(
                self._get_metrics_single_url(metric_type, metric_id)),
            **query_options)
    
    def query_metric_definitions(self, metric_type=None, id_filter=None, **tags):
        """
        Query available metric definitions. Available query options are id_filter for id filtering and tags (dict) as tag based query.
        Tags filtering is required for the id filtering to work.
        """
        if id is not None and tags is None:
            raise HawkularMetricsError('Tags query is required when id filter is used')

        params = {}

        if metric_type is not None:
            params = { 'type': MetricType.short(metric_type) }

        if len(tags) > 0:
            params['tags'] = self._transform_tags(**tags)

        return self._get(self._get_url(), **params)

    def query_tag_values(self, metric_type=None, **tags):
        """
        Query for possible tag values. **tags is a dict which has tagname as key and regexp tagvalue as value. See Hawkular-Metrics
        tag query language for more detailed definition.
        """
        tagql = self._transform_tags(**tags)

        return self._get(self._get_metrics_tags_url(self._get_url(metric_type)) + '/{}'.format(tagql))

    def create_metric_definition(self, metric_type, metric_id, **tags):
        """
        Create metric definition with custom definition. **tags should be a set of tags, such as
        units, env ..
        """
        item = { 'id': metric_id }
        if len(tags) > 0:
            # We have some arguments to pass..
            data_retention = tags.pop('dataRetention',None)
            if data_retention is not None:
                item['dataRetention'] = data_retention

            if len(tags) > 0:
                item['tags'] = tags

        json_data = json.dumps(item, indent=2)
        try:
            self._post(self._get_url(metric_type), json_data)
        except HawkularMetricsError as e:
            if e.code == 409:
                return False
            raise e

        return True
        
    def query_metric_tags(self, metric_type, metric_id):
        """
        Returns a list of tags in the metric definition of metric_id
        """
        definition = self._get(self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)))
        return definition

    def update_metric_tags(self, metric_type, metric_id, **tags):
        """
        Replace the metric_id's tags with given **tags
        """
        self._put(self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)), tags, parse_json=False)

    def delete_metric_tags(self, metric_type, metric_id, **deleted_tags):
        """
        Delete one or more tags from the metric definition. 
        """
        tags = self._transform_tags(**deleted_tags)
        tags_url = self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)) + '/{0}'.format(tags)

        self._delete(tags_url)    
        
    """
    Tenant related queries
    """
    
    def query_tenants(self):
        """
        Query available tenants and their information.
        """
        return self._get(self._get_tenants_url())

    def create_tenant(self, tenant_id, retentions=None):
        """
        Create a tenant. Currently nothing can be set (to be fixed after the master
        version of Hawkular-Metrics has fixed implementation.
        """        
        item = { 'id': tenant_id }
        if retentions is not None:
            item['retentions'] = retentions

        self._post(self._get_tenants_url(), json.dumps(item, indent=2))


"""
Static methods
"""
def time_millis():
    """
    Returns current milliseconds since epoch
    """
    return int(round(time.time() * 1000))

def create_datapoint(value, timestamp=None, **tags):
    """
    Creates a single datapoint dict with a value, timestamp (optional - filled by the method if missing)
    and tags (optional)
    """
    if timestamp is None:
        timestamp = time_millis()

    item = { 'timestamp': timestamp,
             'value': value }

    if tags is not None:
        item['tags'] = tags

    return item

def create_metric(metric_type, metric_id, data):
    """
    Create Hawkular-Metrics' submittable structure, data is a datapoint or list of datapoints
    """
    if not isinstance(data, list):
        data = [data]
    
    return { 'type': metric_type,'id': metric_id, 'data': data }
        
