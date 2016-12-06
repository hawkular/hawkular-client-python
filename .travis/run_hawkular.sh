#!/bin/bash

WAIT_STEP=3
MAX_STEPS=120
HAWKULAR_IMAGE=rubensvp/hawkular-metrics:latest

function metrics_status {
    curl -s http://localhost:8080/hawkular/metrics/status | jq -r '.MetricsService'
}

function alerts_status {
    curl -s http://localhost:8080/hawkular/alerts/status | jq -r '.status'
}

function cassandra_status {
    docker exec hawkular-cassandra nodetool statusbinary | tr -dc '[[:print:]]'
}

function wait_hawkular {
    METRICS_STATUS=$(metrics_status)
    ALERTS_STATUS=$(alerts_status)
    TOTAL_WAIT=0
    while ([ "$METRICS_STATUS" != "STARTED" ] || [ "$ALERTS_STATUS" != "STARTED" ])   && [ ${TOTAL_WAIT} -lt ${MAX_STEPS} ]; do
        METRICS_STATUS=$(metrics_status)
        ALERTS_STATUS=$(alerts_status)
        sleep ${WAIT_STEP}
        echo "Hawkular server status, metrics: $METRICS_STATUS, alerts: $ALERTS_STATUS"
        TOTAL_WAIT=$((TOTAL_WAIT+WAIT_STEP))
        echo "Waited $TOTAL_WAIT seconds for Hawkular metrics to start."
    done
}

function launch_hawkular {
    docker run --name hawkular-metrics -p 8080:8080 --link hawkular-cassandra -d  ${HAWKULAR_IMAGE}
}

function launch_cassandra {
    docker run --name  hawkular-cassandra  -d cassandra:3.7
}

function wait_cassandra {
    CASSANDRA_STATUS=$(cassandra_status)
    TOTAL_WAIT=0;
    while [ "$CASSANDRA_STATUS" != "running" ] && [ ${TOTAL_WAIT} -lt ${MAX_STEPS} ]; do
        CASSANDRA_STATUS=$(cassandra_status)
        echo "Cassandra server status: $CASSANDRA_STATUS."
        sleep ${WAIT_STEP}
        TOTAL_WAIT=$((TOTAL_WAIT+WAIT_STEP))
        echo "Waited $TOTAL_WAIT seconds for Cassandra to start."
    done
}

launch_cassandra
wait_cassandra
launch_hawkular
wait_hawkular