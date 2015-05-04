import unittest
import uuid
from metrics import *

class TestMetricFunctionsBase(unittest.TestCase):

    def setUp(self):
        self.test_tenant = str(uuid.uuid4())
        self.client = HawkularMetricsClient(tenant_id=self.test_tenant, port=8080)
        
class TenantTestCase(TestMetricFunctionsBase):
    """
    Test creating and fetching tenants. Each creation test should also
    fetch the tenants to test that functionality also
    """
    
    def test_tenant_creation(self):
        tenant = str(uuid.uuid4())
        self.client.create_tenant(tenant)
        tenants = self.client.query_tenants()

        expect = { 'id': tenant }
        self.assertIn(expect, tenants)

    def test_tenant_creation_with_retentions_and_aggregations(self):
        # This feature isn't finished in the current master version of Hawkular-Metrics
        pass
        # tenant = str(uuid.uuid4())
        # self.client.create_tenant(tenant, 40)
        # tenants = self.client.query_tenants()

        # expect = { 'id': tenant, 'dataRetention': 40 }
        # self.assertIn(expect, tenants)
        
class MetricsTestCase(TestMetricFunctionsBase):
    """
    Test metric functionality, both adding definition and querying for definition, 
    as well as adding new numeric and availability metrics. 

    Metric definition creation should also test fetching the definition, while
    metric inserts should test also fetching the metric data.
    """
    
    def test_numeric_creation(self):
        """
        Test creating numeric metric definitions with different tags and definition.
        """
        # Create numeric metrics with empty details and added details
        md1 = self.client.create_numeric_definition('test.create.numeric.1')
        md2 = self.client.create_numeric_definition('test.create.numeric.2', dataRetention=90)
        md3 = self.client.create_numeric_definition('test.create.numeric.3', dataRetention=90, units='bytes', env='qa')
        self.assertTrue(md1)
        self.assertTrue(md2)
        self.assertTrue(md3)

        # Fetch metrics definition and check that the ones we created appeared also
        m = self.client.query_definitions(MetricType.Gauge)
        self.assertEqual(3, len(m))
        self.assertEqual(self.test_tenant, m[0]['tenantId'])
        self.assertEqual('bytes', m[2]['tags']['units'])

        # This is what the returned dict should look like
        expect = [
            {'id': 'test.create.numeric.1',
             'tenantId': self.test_tenant },
            {'dataRetention': 90, 'id': 'test.create.numeric.2', 'tenantId': self.test_tenant},
            {'tags': {'units': 'bytes', 'env': 'qa'},
             'id': 'test.create.numeric.3', 'dataRetention': 90, 'tenantId': self.test_tenant}]

        self.assertEqual(m, expect) # Did it?

        # Lets try creating a duplicate metric
        md4 = self.client.create_numeric_definition('test.create.numeric.1')
        self.assertFalse(md4, 'Should have received an exception, metric with the same name was already created')

    def test_availability_creation(self):
        # Create availability metric
        # Fetch mterics and check that it did appear
        self.client.create_availability_definition('test.create.avail.1')
        self.client.create_availability_definition('test.create.avail.2', dataRetention=90)
        self.client.create_availability_definition('test.create.avail.3', dataRetention=94, env='qa')
        # Fetch metrics and check that it did appear
        m = self.client.query_definitions(MetricType.Availability)        
        self.assertEqual(3, len(m))
        self.assertEqual(94, m[2]['dataRetention'])

    def test_tags_modifications(self):
        m = 'test.create.tags.1'
        # Create metric without tags
        self.client.create_numeric_definition(m)
        e = self.client.query_metric_tags(MetricType.Gauge, m)
        self.assertIsNotNone(e)
        self.assertEqual({}, e)
        # Add tags
        self.client.update_metric_tags(MetricType.Gauge, m, hostname='machine1', a='b')
        # Fetch metric - check for tags
        tags = self.client.query_metric_tags(MetricType.Gauge, m)
        self.assertEqual(2, len(tags))
        self.assertEqual("b", tags['a'])
        # Delete some metric tags
        self.client.delete_metric_tags(MetricType.Gauge, m, a='b', hostname='machine1')
        # Fetch metric - check that tags were deleted
        tags_2 = self.client.query_metric_tags(MetricType.Gauge, m)
        self.assertEqual(0, len(tags_2))

    # def test_tags_behavior(self):
    #     print 'START: TEST TAGS'
    #     metric = float(1.2345)
    #     print 'CREATE'
    #     self.client.create_numeric_definition('test.numeric.single.tags.1', hostname='')
    #     print 'POST'
    #     self.client.push('test.numeric.single.tags.1', metric, hostname='localhost')
    #     print 'GET'
    #     data = self.client.query_single_numeric('test.numeric.single.tags.1')
    #     print data
    #     print 'END: TEST TAGS'
    
    def test_add_numeric_single(self):
        # Normal way
        value = float(4.35)
        datapoint = create_datapoint(value, time_millis())
        metric = create_metric(MetricType.Gauge, 'test.numeric./', datapoint)
        self.client.put(metric)

        # Fetch results
        data = self.client.query_single_numeric('test.numeric./')
        self.assertEqual(float(data[0]['value']), value)

        # Shortcut method with tags
        self.client.push(MetricType.Gauge, 'test.numeric.single.tags', value, hostname='localhost')

        # Fetch results
        data = self.client.query_single_numeric('test.numeric.single.tags')
        self.assertEqual(value, float(data[0]['value']))
        # self.assertEqual(data[0]['tags']['localhost'], 'localhost')

    def test_add_availability_single(self):
        self.client.push(MetricType.Availability, 'test.avail.1', Availability.Up)
        self.client.push(MetricType.Availability, 'test.avail.2', 'down')

        up = self.client.query_single_availability('test.avail.1')
        self.assertEqual(up[0]['value'], 'up')
        
        down = self.client.query_single_availability('test.avail.2')
        self.assertEqual(down[0]['value'], Availability.Down)

    def test_add_numeric_multi_datapoint(self):
        metric_1v = create_datapoint(float(1.45))
        metric_2v = create_datapoint(float(2.00), (time_millis() - 2000))

        metric = create_metric(MetricType.Gauge, 'test.numeric.multi', [metric_1v, metric_2v])
        self.client.put(metric)
        
        data = self.client.query_single_numeric('test.numeric.multi')
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['value'], float(1.45))
        self.assertEqual(data[1]['value'], float(2.00))

    def test_add_availability_multi_datapoint(self):
        t = time_millis()
        up = create_datapoint('up', (t - 2000))
        down = create_datapoint('down', t)

        m = create_metric(MetricType.Availability, 'test.avail.multi', [up, down])
        
        self.client.put(m)
        data = self.client.query_single_availability('test.avail.multi')

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['value'], 'up')
        self.assertEqual(data[1]['value'], 'down')

    def test_add_mixed_metrics_and_datapoints(self):
        metric1 = create_datapoint(float(1.45))
        metric1_2 = create_datapoint(float(2.00), (time_millis() - 2000))

        metric_multi = create_metric(MetricType.Gauge, 'test.multi.numeric.1', [metric1, metric1_2])

        metric2 = create_datapoint(Availability.Up)
        metric2_multi = create_metric(MetricType.Availability,'test.multi.numeric.2', [metric2])

        self.client.put([metric_multi, metric2_multi])

        # Check that both were added correctly..
        metric1_data = self.client.query_single_numeric('test.multi.numeric.1')
        metric2_data = self.client.query_single_availability('test.multi.numeric.2')

        self.assertEqual(2, len(metric1_data))
        self.assertEqual(1, len(metric2_data))

    def test_query_options(self):
        # Create metric with two values
        t = time_millis()
        v1 = create_datapoint(float(1.45), t)
        v2 = create_datapoint(float(2.00), (t - 2000))

        m = create_metric(MetricType.Gauge, 'test.query.numeric.1', [v1, v2])
        self.client.put(m)

        # Query first without limitations
        d = self.client.query_metric(MetricType.Gauge, 'test.query.numeric.1')
        self.assertEqual(2, len(d))

        # Query for data which has start time limitation
        d = self.client.query_metric(MetricType.Gauge, 'test.query.numeric.1', start=(t-1000))
        self.assertEqual(1, len(d))

    # This feature isn't really ready for prime time in Hawkular-Metrics yet.. 
    # def test_tags_finding(self):        
    #     # Create metrics with tags
    #     m = 'test.create.data.tags.1'
    #     self.client.create_metric_definition(MetricType.Gauge, m, ab='cd')
    #     # Push some data to them
    #     t = time_millis()
    #     v = float(1.4)
    #     self.client.push(MetricType.Gauge, m, v, t)
    #     # Fetch data with certain tags
    #     expected = { 'id': m, 'timestamp': t, 'value': v }
    #     d = self.client.query_data_with_tags(MetricType.Gauge, ab='cd')
    #     self.assertIsNotNone(d)
    #     self.assertIn(expected, d)        
        
if __name__ == '__main__':
    unittest.main()
