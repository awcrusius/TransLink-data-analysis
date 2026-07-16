import os
import sys

import duckdb
import pytest
from google.transit import gtfs_realtime_pb2

# The ETL scripts live in gtfs_realtime_container/ and import each other as
# top-level modules (`from etl_helper import *`), so put that directory on
# sys.path for the tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import etl_helper  # noqa: E402


@pytest.fixture(autouse=True)
def reset_api_modifier():
    """Rotated_api_link keeps its round-robin state in a module-level global;
    reset it so tests are order-independent."""
    etl_helper.api_modifier = 0
    yield
    etl_helper.api_modifier = 0


@pytest.fixture
def db():
    """In-memory DuckDB connection with the three rt_* tables created."""
    conn = duckdb.connect(':memory:')
    etl_helper.create_rt_position(conn)
    etl_helper.create_rt_trip(conn)
    etl_helper.create_rt_alerts(conn)
    yield conn
    conn.close()


def make_position_feed(trip_id='trip-1', vehicle_id='veh-1', timestamp=1752600000):
    """Build a small FeedMessage containing one vehicle position entity."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    feed.header.timestamp = timestamp

    entity = feed.entity.add()
    entity.id = 'entity-' + trip_id
    vehicle = entity.vehicle
    vehicle.trip.trip_id = trip_id
    vehicle.trip.start_date = '20260716'
    vehicle.trip.schedule_relationship = 0
    vehicle.trip.route_id = 'route-99'
    vehicle.trip.direction_id = 1
    vehicle.position.latitude = 49.2827
    vehicle.position.longitude = -123.1207
    vehicle.current_stop_sequence = 7
    vehicle.current_status = 2  # IN_TRANSIT_TO
    vehicle.timestamp = timestamp
    vehicle.stop_id = 'stop-42'
    vehicle.vehicle.id = vehicle_id
    vehicle.vehicle.label = 'Bus 99'
    return feed


def make_trip_feed(trip_id='trip-1', vehicle_id='veh-1', stop_ids=('stop-1', 'stop-2')):
    """Build a FeedMessage with one trip update carrying one stop_time_update
    per entry in stop_ids (so tests can prove only the first is ingested)."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    feed.header.timestamp = 1752600000

    entity = feed.entity.add()
    entity.id = 'entity-' + trip_id
    trip_update = entity.trip_update
    trip_update.trip.trip_id = trip_id
    trip_update.trip.start_date = '20260716'
    trip_update.trip.schedule_relationship = 0
    trip_update.trip.route_id = 'route-99'
    trip_update.trip.direction_id = 1
    trip_update.vehicle.id = vehicle_id
    trip_update.vehicle.label = 'Bus 99'

    for i, stop_id in enumerate(stop_ids):
        stu = trip_update.stop_time_update.add()
        stu.stop_sequence = i + 1
        stu.stop_id = stop_id
        stu.arrival.delay = 60 * (i + 1)
        stu.arrival.time = 1752600300 + 600 * i
        stu.departure.delay = 90 * (i + 1)
        stu.departure.time = 1752600360 + 600 * i
        stu.schedule_relationship = 0
    return feed


def make_alert_feed(alert_id='alert-1', period_start=1752590000, period_end=1752690000):
    """Build a FeedMessage with one service alert affecting two routes/stops."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    feed.header.timestamp = 1752600000

    entity = feed.entity.add()
    entity.id = alert_id
    alert = entity.alert
    period = alert.active_period.add()
    period.start = period_start
    period.end = period_end
    for route_id, route_type, stop_id in [('route-1', 3, 'stop-1'), ('route-2', 3, 'stop-2')]:
        informed = alert.informed_entity.add()
        informed.route_id = route_id
        informed.route_type = route_type
        informed.stop_id = stop_id
    alert.cause = 1  # OTHER_CAUSE
    alert.effect = 4  # DETOUR
    alert.severity_level = 3  # WARNING
    translation = alert.header_text.translation.add()
    translation.text = 'Detour on route-1 and route-2'
    translation.language = 'en'
    return feed
