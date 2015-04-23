import json
import urllib2
import urllib
import time

"""
TODO: Remember to do imports for Python 3 also and check the compatibility..
TODO: Search datapoints with tags.. tag datapoints.
TODO: Allow changing instance's tenant?
TODO: Authentication when it's done..
TODO: Remove HawkularMetricsConnectionError and use HawkularMetricsError only?
TODO: 0.3.3 will change /hawkular-metrics to hawkular/metrics and the REST-interfaces
"""

class MetricType:
    Numeric = 'numeric'
    Availability = 'availability'

    @staticmethod
    def short(metric_type):
        if metric_type is 'numeric':
            return 'num'
        else:
            return 'avail'

class Availability:
    Down = 'down'
    Up = 'up'

class HawkularMetricsError(urllib2.HTTPError):
    pass
        
class HawkularMetricsConnectionError(urllib2.URLError):
    pass

class HTTPErrorProcessor(urllib2.HTTPErrorProcessor):
    """
    Hawkular-Metrics uses http codes 201, 204
    """
    def http_response(self, request, response):

        if response.code in [200, 201, 204]:
            return response
        return urllib2.HTTPErrorProcessor.http_response(self, request, response)
  
    https_response = http_response

class HawkularMetricsClient:
    """
    Creates new client for Hawkular-Metrics. As tenant_id, give intended tenant_id, even if it's not
    created yet. Use one instance of HawkularMetricsClient for each tenant.
    """
    def __init__(self,
                 tenant_id,
                 host='localhost',
                 port=8081,
                 path='hawkular-metrics'):
        """
        A new instance of HawkularMetricsClient is created with the following defaults:

        host = localhost
        port = 8081
        path = hawkular-metrics

        The url that is called by the client is:

        http://{host}:{port}/{2}/
        """
        self.tenant_id = tenant_id
        self.host = host
        self.port = port
        self.path = path

        opener = urllib2.build_opener(HTTPErrorProcessor())
        urllib2.install_opener(opener)

    """
    Internal methods
    """
    @staticmethod
    def _clean_metric_id(metric_id):
        return urllib.quote(metric_id, '')

    def _get_base_url(self):
        return "http://{0}:{1}/{2}/".format(self.host, str(self.port), self.path)
    
    def _get_url(self, service):
        return self._get_base_url() + '{0}/{1}'.format(self.tenant_id, service)

    def _get_metrics_url(self, metric_type):
        return self._get_url('metrics') + "/{0}".format(metric_type)

    def _get_metrics_single_url(self, metric_type, metric_id):
        return self._get_metrics_url(metric_type) + '/{0}'.format(self._clean_metric_id(metric_id))
    
    def _get_metrics_data_url(self, metrics_url):
        return metrics_url + '/data'

    def _get_metrics_tags_url(self, metrics_url):
        return metrics_url + '/tags'

    def _get_tenants_url(self):
        return self._get_base_url() + 'tenants'
    
    def _http(self, url, method, data=None):
        res = None

        try:
            req = urllib2.Request(url=url)
            req.add_header('Content-Type', 'application/json')

            if not isinstance(data, str):
                data = json.dumps(data, indent=2)

            if data:
                req.add_data(data)

            req.get_method = lambda: method    
            res = urllib2.urlopen(req)
            if method == 'GET':
                if res.getcode() == 200:
                    data = json.load(res)
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
        params = urllib.urlencode(url_params)
        if len(params) > 0:
            url = '{0}?{1}'.format(url, params)
            
        return self._http(url, 'GET')        
        
    def _handle_error(self, e):
        if isinstance(e, urllib2.HTTPError):
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
        elif isinstance(e, urllib2.URLError):
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

    """
    Instance methods
    """
    
    def put(self, metric_type, data):
        """
        Send multiple different metric_ids to the server in a single
        batch.

        data is a dict or a list of dicts created with create_metric(metric_id, metric_dict)
        """
        if not isinstance(data, list):
            data = [data]
            
        self._post(self._get_metrics_data_url(self._get_metrics_url(metric_type)), data)

    def push(self, metric_type, metric_id, value, timestamp=None, **tags):
        """
        Pushes a single metric_id, datapoint combination to the server.

        This method is an assistant method for the put method by removing the need to
        create data structures first.
        """
        item = create_metric(metric_id, create_datapoint(value, timestamp, **tags))
        self.put(metric_type, item)

    def query_metric(self, metric_type, metric_id, **search_options):
        """
        Query for metrics from the server. 

        Supported search options are [optional]: start, end and buckets

        Use methods query_single_numeric and query_single_availability for simple access
        """
        return self._get(
            self._get_metrics_data_url(
                self._get_metrics_single_url(metric_type, metric_id)),
            **search_options)

    def query_single_numeric(self, metric_id, **search_options):
        """
        See query_metric
        """
        return self.query_metric(MetricType.Numeric, metric_id, **search_options)

    def query_single_availability(self, metric_id, **search_options):
        """
        See query_metric
        """
        return self.query_metric(MetricType.Availability, metric_id, **search_options)
    
    def query_definitions(self, query_type):
        """
        Query available metric definitions. Use 'avail' or 'num' or MetricType.Availability / MetricType.Numeric
        """
        if isinstance(query_type, MetricType):
            query_type = MetricType.short(query_type)
            
        definition_url = self._get_url('metrics') + '?type=' + MetricType.short(query_type)
        return self._get(definition_url)

    def create_metric_definition(self, metric_type, metric_id, **tags):
        """
        Create metric definition with custom definition. **options should be a set of tags, such as
        units, env ..

        Use methods create_numeric_definition and create_availability_definition to avoid using
        MetricType.Numeric / MetricType.Availability
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
        self._post(self._get_metrics_url(metric_type), json_data)

    def create_numeric_definition(self, metric_id, **tags):
        """
        See create_metric_definition
        """
        self.create_metric_definition(MetricType.Numeric, metric_id, **tags)

    def create_availability_definition(self, metric_id, **tags):
        """
        See create_metric_definition
        """
        self.create_metric_definition(MetricType.Availability, metric_id, **tags)
        
    def query_metric_tags(self, metric_type, metric_id):
        """
        Returns a list of tags in the metric definition of metric_id
        """
        definition = self._get(self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)))
        return definition.get('tags', {})

    def update_metric_tags(self, metric_type, metric_id, **tags):
        """
        Replace the metric_id's tags with given **tags
        """
        self._put(self._get_metrics_tags_url(self._get_metrics_single_url(metric_type, metric_id)), tags)

    def delete_metric_tags(self, metric_type, metric_id, **deleted_tags):
        """
        Delete one or more tags from the metric definition. The tag values must match what's stored on the server.
        """
        tags = ','.join("%s:%s" % (key,val) for (key,val) in deleted_tags.iteritems())
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

    def create_tenant(self, tenant_id):
        """
        Create a tenant. Currently nothing can be set (to be fixed after the master
        version of Hawkular-Metrics has fixed implementation.
        """        
        item = { 'id': tenant_id }

        # if retention_time is not None:
        #     item['dataRetention'] = retention_time

        # if len(tags) > 0:
        #     item.extend(tags)

        tenants_url = self._get_tenants_url()
        self._post(tenants_url, json.dumps(item, indent=2))

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

def create_metric(metric_id, data):
    """
    Create Hawkular-Metrics' submittable structure, data is a datapoint or list of datapoints
    """
    if not isinstance(data, list):
        data = [data]
    
    return { 'id': metric_id, 'data': data }
        
