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

try:
    # Python 3
    from urllib.request import Request, urlopen, build_opener, install_opener, HTTPErrorProcessor
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote, urlencode, quote_plus
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import Request, urlopen, URLError, HTTPError, HTTPErrorProcessor, build_opener, install_opener
    from urllib import quote, urlencode, quote_plus


class ApiJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ApiOject):
            return obj.to_json_object()
        else:
            return json.JSONEncoder.default(self, obj)


class HawkularMetricsError(HTTPError):
    pass


class HawkularMetricsConnectionError(URLError):
    pass


class HawkularMetricsStatusError(ValueError):
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


class ApiOject:

    defaults = dict()

    def __init__(self, dictionary=dict()):
        udict = ApiOject.transform_dict_to_underscore(dictionary)
        for k in self.__slots__:
            setattr(self, k, udict.get(k,self.defaults.get(k)))

    def to_json_object(self):
        dictionary = {}
        for attribute in self.__slots__:
            if hasattr(self,attribute):
                dictionary[attribute] = getattr(self,attribute)
        return ApiOject.transform_dict_to_camelcase(dictionary)

    @staticmethod
    def _to_camelcase(word):
        s = ''.join(x.capitalize() or '_' for x in word.split('_'))
        return ''.join([s[0].lower(), s[1:]])

    @staticmethod
    def _to_underscore(word):
        return ''.join(["_" + c.lower() if c.isupper() else c for c in word]).strip('_')

    @staticmethod
    def transform_dict_to_camelcase(dictionary):
        if dictionary is None:
            return dict()
        return dict((ApiOject._to_camelcase(k), v) for k, v in dictionary.items() if v is not None)

    @staticmethod
    def transform_dict_to_underscore(dictionary):
        if dictionary is None:
            return dict()
        return dict((ApiOject._to_underscore(k), v) for k, v in dictionary.items() if v is not None)

    @classmethod
    def list_to_object_list(cls, o):
        if o is not None:
            return [cls(ob) for ob in o]
        return []


class HawkularHTTPErrorProcessor(HTTPErrorProcessor):
    """
    Hawkular-Metrics uses http codes 201, 204
    """

    def http_response(self, request, response):
        if response.code in [200, 201, 204]:
            return response
        return HTTPErrorProcessor.http_response(self, request, response)

    https_response = http_response


class HawkularBaseClient:
    """
    Creates new client for Hawkular-Metrics. As tenant_id, give intended tenant_id, even if it's not
    created yet. To change the instance's tenant_id, use tenant(tenant_id) method
    """
    def __init__(self,
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
                 authtoken=None):
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
        self.context = context
        self.token = token
        self.username = username
        self.password = password
        self.legacy_api = False
        self.authtoken = authtoken

        opener = build_opener(HawkularHTTPErrorProcessor())
        install_opener(opener)

        if path is None:
            class_name = self.__class__.__name__
            path_components = ''.join(["_" + c.lower() if c.isupper() else c for c in class_name]).split('_')
            path_components.pop()
            self.path = '/'.join(path_components);
        else:
            self.path = path
        self.path = self.path.strip('/')

        # Call the server status endpoint to get the version number,
        # Use the return sematic version to set the value of legacy_api
        if auto_set_legacy_api:
            major, minor = self.query_semantic_version()
            self.legacy_api = (major == 0 and minor < 16)

    def _get_base_url(self):
        return "{0}://{1}:{2}/{3}/".format(self.scheme, self.host, str(self.port), self.path)

    def _get_status_url(self):
        return self._get_base_url() + 'status'

    def tenant(self, tenant_id):
        self.tenant_id = tenant_id

    def _http(self, url, method, data=None, decoder=None, parse_json=True):
        res = None
        req = Request(url=url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Hawkular-Tenant', self.tenant_id)
        req.add_header('Host', self.host)

        if self.token is not None:
            req.add_header('Authorization', 'Bearer {0}'.format(self.token))
        elif self.username is not None:
            b64 = base64.b64encode(bytes(self.username + ':' + self.password, encoding='utf-8'))
            req.add_header('Authorization',
                           'Basic {0}'.format(b64))

        if self.authtoken is not None:
            req.add_header('Hawkular-Admin-Token', self.authtoken)

        if not isinstance(data, str):
            data = json.dumps(data, indent=2)

        reader = codecs.getreader('utf-8')

        if data:
            try:
                req.add_data(data)
            except AttributeError:
                req.data = data.encode('utf-8')
        try:
            req.get_method = lambda: method
            res = urlopen(req, context=self.context)

            if parse_json:
                if res.getcode() == 200:
                    data = json.load(reader(res), cls=decoder)
                elif res.getcode() == 204:
                    data = {}
            else:
                data = reader(res).read()

            return data

        except Exception as e:
            self._handle_error(e)

        finally:
            if res:
                res.close()

    def _put(self, url, data, parse_json=True):
        return self._http(url, 'PUT', data, parse_json=parse_json)

    def _delete(self, url, parse_json=False):
        return self._http(url, 'DELETE', parse_json=parse_json)

    def _post(self, url, data, parse_json=True):
        return self._http(url, 'POST', data, parse_json=parse_json)

    def _get(self, url, **url_params):
        params = urlencode(url_params)
        if len(params) > 0:
            url = '{0}?{1}'.format(url, params)

        return self._http(url, 'GET')

    def _service_url(self, path, params=None):
        url_array = [self._get_base_url()]

        str_path = path
        if isinstance(path,list):
            encoded_path = [quote_plus(p) for p in path]
            str_path  = '/'.join(encoded_path).strip('/')

        url_array.append(str_path)
        if params is not None:
            query = ''.join(['?', urlencode(params)])
            url_array.append(query)

        return ''.join(url_array)

    @staticmethod
    def _serialize_object(o):
        return json.dumps(o, cls=ApiJsonEncoder)

    def _handle_error(self, e):
        if isinstance(e, HTTPError):
            # Cast to HawkularMetricsError
            ee = HawkularMetricsError(e.url, e.code, e.msg, e.hdrs, e.fp)
            err_json = e.read()

            try:
                err_d = json.loads(err_json)
                ee.msg = err_d['errorMsg']
            except:
                # Keep the original payload, couldn't parse it
                ee.msg = err_json
            raise ee

        elif isinstance(e, URLError):
            # Cast to HawkularMetricsConnectionError
            ee = HawkularMetricsConnectionError()
            ee.msg = "Error, could not send event(s) to the Hawkular Metrics: " + str(e.reason)
            raise ee
        elif isinstance(e, KeyError):
            # Cast to HawkularMetricsStatusError
            ee = HawkularMetricsStatusError
            ee.msg = "Error, unable to get implementation version for metrics: " + str(e.reason)
            raise ee
        elif isinstance(e, ValueError):
            # Cast to HawkularMetricsStatusError
            ee = HawkularMetricsStatusError
            ee.msg = "Error, unable to determine implementation version for metrics: " + str(e.reason)
            raise ee
        else:
            raise e
    """
    General information related queries
    """
    def query_semantic_version(self):
        status_hash = self.query_status()
        try:
            version = status_hash['Implementation-Version']
            major, minor = map(int, version.split('.')[:2])
        except Exception as e:
            self._handle_error(e)
        return major, minor

    def query_status(self):
        return self._get(self._get_status_url())

    @staticmethod
    def quote(value,safe=''):
        return quote(value, safe)