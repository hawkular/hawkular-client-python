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
import json
import time
import collections

try:
    # Python 3
    from urllib.request import Request, urlopen, build_opener, install_opener, HTTPErrorProcessor
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote, urlencode
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import Request, urlopen, URLError, HTTPError, HTTPErrorProcessor, build_opener, install_opener
    from urllib import quote, urlencode

class MetricType:
    Gauge = 'gauges'
    Availability = 'availability'
    Counter = 'counters'
    Rate = 'rate'
    _Metrics = 'metrics'

    @staticmethod
    def short(metric_type):
        if metric_type is MetricType.Gauge:
            return 'gauge'
        elif metric_type is MetricType.Counter:
            return 'counter'
        else:
            return 'availability'

class Availability:
    Down = 'down'
    Up = 'up'
    Unknown = 'unknown'

class HawkularMetricsError(HTTPError):
    pass
        
class HawkularMetricsConnectionError(URLError):
    pass

class HawkularHTTPErrorProcessor(HTTPErrorProcessor):
    """
    Hawkular-Metrics uses http codes 201, 204
    """
    def http_response(self, request, response):

        if response.code in [200, 201, 204]:
            return response
        return HTTPErrorProcessor.http_response(self, request, response)
  
    https_response = http_response

class HawkularMetricsClient:
    """
    Creates new client for Hawkular-Metrics. As tenant_id, give intended tenant_id, even if it's not
    created yet. To change the instance's tenant_id, use tenant(tenant_id) method
    """
    def __init__(self,
                 tenant_id,
                 host='localhost',
                 port=8080,
                 path='hawkular/metrics',
                 scheme='http',
                 cafile=None,
                 token=None):
        """
        A new instance of HawkularMetricsClient is created with the following defaults:

        host = localhost
        port = 8081
        path = hawkular-metrics
        scheme = http
        cafile = None

        The url that is called by the client is:

        {scheme}://{host}:{port}/{2}/
        """
        self.tenant_id = tenant_id
        self.host = host
        self.port = port
        self.path = path
        self.cafile = cafile
        self.scheme = scheme
        self.token = token

        opener = build_opener(HawkularHTTPErrorProcessor())
        install_opener(opener)

    """
    Internal methods
    """
    @staticmethod
    def _clean_metric_id(metric_id):
        return quote(metric_id, '')

    def _get_base_url(self):
        return "{0}://{1}:{2}/{3}/".format(self.scheme, self.host, str(self.port), self.path)
    
    def _get_url(self, metric_type=None):
        if metric_type is None:
            metric_type = MetricType._Metrics

        return self._get_base_url() + '{0}'.format(metric_type)

    def _get_metrics_single_url(self, metric_type, metric_id):
        return self._get_url(metric_type) + '/{0}'.format(self._clean_metric_id(metric_id))

    def _get_metrics_raw_url(self, metrics_url):
        return metrics_url + '/raw'

    def _get_metrics_stats_url(self, metrics_url):
        return metrics_url + '/stats'

    def _get_metrics_tags_url(self, metrics_url):
        return metrics_url + '/tags'

    def _get_tenants_url(self):
        return self._get_base_url() + 'tenants'

    @staticmethod
    def _transform_tags(**tags):
        return ','.join("%s:%s" % (key,val) for (key,val) in tags.items())
    
    def _http(self, url, method, data=None):
        res = None

        try:
            req = Request(url=url)
            req.add_header('Content-Type', 'application/json')
            req.add_header('Hawkular-Tenant', self.tenant_id)

            if self.token is not None:
                req.add_header('Authorization', 'Bearer {0}'.format(self.token))

            if not isinstance(data, str):
                data = json.dumps(data, indent=2)

            # writer = codecs.getencoder('utf-8')
            reader = codecs.getreader('utf-8')

            if data:
                try:
                    req.add_data(data)
                except AttributeError:
                    req.data = data.encode('utf-8')

            req.get_method = lambda: method
            res = urlopen(req)
            if method == 'GET':
                if res.getcode() == 200:
                    data = json.load(reader(res))

                elif res.getcode() == 204:
                    data = {}

                return data

        except Exception as e:
            self._handle_error(e)

        finally:
            if res:
                res.close()        
    
    def _put(self, url, data):
        self._http(url, 'PUT', data)

    def _delete(self, url):
        self._http(url, 'DELETE')    
        
    def _post(self, url, data):
        self._http(url, 'POST', data)

    def _get(self, url, **url_params):
        params = urlencode(url_params)
        if len(params) > 0:
            url = '{0}?{1}'.format(url, params)

        return self._http(url, 'GET')        
        
    def _handle_error(self, e):
        if isinstance(e, HTTPError):
            # Cast to HawkularMetricsError
            e.__class__ = HawkularMetricsError
            err_json = e.read()

            try:
                err_d = json.loads(err_json)
                e.msg = err_d['errorMsg']
            except:
                # Keep the original payload, couldn't parse it
                e.msg = err_json

            raise e
        elif isinstance(e, URLError):
            # Cast to HawkularMetricsConnectionError
            e.__class__ = HawkularMetricsConnectionError
            e.msg = "Error, could not send event(s) to the Hawkular Metrics: " + str(e.reason)
            raise e
        else:
            raise e
        
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
            self._post(self._get_metrics_raw_url(self._get_url(l)), r[l])

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
        self._put(self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)), tags)

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
        
