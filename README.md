[![Build Status](https://travis-ci.org/hawkular/hawkular-client-python.svg?branch=master)](https://travis-ci.org/hawkular/hawkular-client-python)

hawkular-client-python
=========================

This repository includes the necessary Python client libraries to access Hawkular remotely. Currently we only have a driver for the metrics and alerts components.

## Introduction

Python client to access Hawkular-Metrics, an abstraction to invoke REST-methods on the server endpoint using urllib2. No external dependencies, works with Python 2.7.x (tested on 2.7.14) and Python 3.4.x / 3.5.x / 3.6.x (tested with the Python 3.4.2, Python 3.5.3 and Python 3.6.4, might work with newer versions also).

## License and copyright

```
   Copyright 2015-2018 Red Hat, Inc. and/or its affiliates
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
```

## Installation

To install, run ``python setup.py install`` if you installed from source code, or ``pip install hawkular-client`` if using pip.

## Metrics Usage

To use hawkular-client-python in your own program, after installation import from hawkular the class HawkularMetricsClient and instantiate it. After this, push dicts with keys id, timestamp and value with put or use assistant method create to send events. pydoc gives the list of allowed parameters for each function.

The client provides a method to request current time in milliseconds, ``time_millis()`` that's accepted by the methods, but you can use ``datetime`` and ``timedelta`` to control the time also when sending requests to the Hawkular-Metrics. 

See ``tests/test_metrics.py`` for more detailed examples and [Hawkular-Metrics documentation](http://www.hawkular.org/hawkular-metrics/docs/user-guide/) for more detailed explanation of available features.

### General

When a method wants a metric_type one can use the shortcuts of from MetricType class (Gauge, Availability and Counter). For availability values, one can use values Availability.Up and Availability.Down to simplify usage.

To instantiate the client, use HawkularMetricsClient() method. It requires something given as tenant_id, even if the tenant does not exists yet (it is not auto-created, you have to call ``create_tenant(tenant_id)`` to create it). To change the target tenant_id, use ``tenant(tenant_id)``

```python
>>> from hawkular.metrics import HawkularMetricsClient, MetricType
>>> client = HawkularMetricsClient(tenant_id='python_test')
```

### Creating and modifying metric definitions

While creating a metric definition is not required, it is recommended to avoid duplicate metric_ids, which could cause silent data overwriting. It is possible to define a custom data retention times as well as tags for each metric. To create a metric, use method ``create_metric_definition(metric_id, metric_type, **tags)`` The only reserved keyword for tags is dataRetention, which will change the dataRetention time, other tag names are used for user's metadata.

Example:

```python
>>> client.create_metric_definition(MetricType.Gauge, 'example.doc.1', units='bytes', env='test')
True
>>> client.query_metric_definitions(MetricType.Gauge)
[{'type': 'gauge', 'id': 'example.doc.1', 'tags': {'units': 'bytes', 'env': 'test'}, 'tenantId': 'python_test', 'dataRetention': 7}]
```

### Modifying metric definition tags

One powerful feature of Hawkular-Metrics is the tagging feature that allows one to define descriptive metadata for any metric. Tags can be added when creating a metric definition (see above), but also modified later. By tagging the definitions, you can search for matching definitions with the tag query language.

Example:

```python
>>> client.create_metric_definition(MetricType.Gauge, 'example.doc.2', units='bytes', env='test', hostname='testenv01')
>>> client.query_metric_tags(MetricType.Gauge, 'example.doc.2')
{'units': 'bytes', 'hostname': 'testenv01', 'env': 'test'}
```

To search all the metric definitions with a given tags and tag values, use the ``query_definitions()``

```python
>>> client.query_metric_definitions(MetricType.Gauge, hostname='testenv.*')
[{'type': 'gauge', 'id': 'example.doc.2', 'tags': {'units': 'bytes', 'hostname': 'testenv01', 'env': 'test'}, 'tenantId': 'python_test', 'dataRetention': 7}]
```

It is also possible to query all the available tag values, in case you want to list for example the hostnames that have metrics information gathered.

```python
>>> client.query_tag_values(hostname='*')
{'hostname': ['testenv01', 'prodenv01']}
```

### Pushing new values

All the methods that allow pushing values can accept both availability status as well as float values. It is possible to push multiple metrics with multiple values per metric in one call to the Hawkular-Metrics. However for convenience, a method which will push just one value for one metric is also provided. To push availability values, use MetricType.Availability and values Availability.Up and Availability.Down, otherwise the syntax is equal.

``create_datapoint(value)`` and ``create_metric(metric_type, metric_id, datapoints)`` return the necessary structures requested by the multi-functions.

Example pushing a multiple values:

```python
>>> from hawkular.metrics import create_datapoint, create_metric, time_millis
>>> t = datetime.utcnow()
>>> datapoint = create_datapoint(float(4.35), t)
>>> datapoint2 = create_datapoint(float(4.42), t + timedelta(seconds=10))
>>> metric = create_metric(MetricType.Gauge, 'example.doc.1', [datapoint, datapoint2])
>>> client.put(metric)
```

And a shortcut method to push just a single value with automatically generated timestamp:

```python
>>> client.push(MetricType.Gauge, 'example.doc.1', float(4.24))
```

To push multiple metrics with multiple values per metric, see metrics_test.py and method ``test_add_multi_metrics_and_datapoints()``.

### Querying metric values

Querying metrics and its raw values happens through the method ``query_metric(metric_type, metric_id, **query_options)``. Available options are listed in the Hawkular-Metrics documentation. To query for aggregated values, use the method ``query_metric_stats(metric_type, metric_id, **query_options)``

Example querying for raw values:

```python
>>> client.query_metric(MetricType.Gauge, 'example.doc.1')
[{'value': 4.24, 'timestamp': 1462363124102}, {'value': 4.42, 'timestamp': 1462363032249}, {'value': 4.35, 'timestamp': 1462362981464}]
>>> client.query_metric(MetricType.Gauge, 'example.doc.1', start=1462363032249)
[{'value': 4.24, 'timestamp': 1462363124102}, {'value': 4.42, 'timestamp': 1462363032249}]
```

For aggregated metrics:

```python
>>> client.query_metric_stats(MetricType.Gauge, 'example.doc.1', buckets=2, percentiles='90.0,95.0')
[{'empty': True, 'start': 1462334779765, 'end': 1462349179765}, {'empty': False, 'avg': 4.336666666666667, 'start': 1462349179765, 'min': 4.24, 'samples': 3, 'sum': 13.01, 'max': 4.42, 'end': 1462363579765, 'median': 4.35, 'percentiles': [{'value': 4.35, 'quantile': 0.9}, {'value': 4.35, 'quantile': 0.95}]}]
>>>
```

## Method documentation

Method documentation is available with ``pydoc hawkular``
