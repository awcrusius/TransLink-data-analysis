"""Live integration tests against the real TransLink GTFS-realtime API.

These are opt-in and never run in a normal CI build. To run them locally:

    export TRANSLINK_API_KEY=<your key>
    pytest gtfs_realtime_container/tests -m integration

Without TRANSLINK_API_KEY set, every test here is skipped automatically.
Each test costs one API call against the key's daily quota.
"""

import os

import duckdb
import pytest

import etl_helper

API_KEY = os.environ.get('TRANSLINK_API_KEY', '')

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not API_KEY, reason='TRANSLINK_API_KEY not set'),
]

BASE = 'https://gtfsapi.translink.ca/v3/'


@pytest.fixture
def db():
    conn = duckdb.connect(':memory:')
    etl_helper.create_rt_position(conn)
    etl_helper.create_rt_trip(conn)
    etl_helper.create_rt_alerts(conn)
    yield conn
    conn.close()


def test_live_position_feed_ingests(db):
    feed = etl_helper.get_feed(BASE + 'gtfsposition?apikey=' + API_KEY)
    assert feed is not None
    etl_helper.insert_rt_position(db, feed)
    count = db.sql('SELECT count(*) FROM rt_position').fetchone()[0]
    assert count == len(feed.entity)


def test_live_trip_feed_ingests(db):
    feed = etl_helper.get_feed(BASE + 'gtfsrealtime?apikey=' + API_KEY)
    assert feed is not None
    etl_helper.insert_rt_trip(db, feed)
    count = db.sql('SELECT count(*) FROM rt_trip').fetchone()[0]
    assert count > 0 or len(feed.entity) == 0


def test_live_alerts_feed_ingests(db):
    feed = etl_helper.get_feed(BASE + 'gtfsalerts?apikey=' + API_KEY)
    assert feed is not None
    etl_helper.insert_rt_alerts(db, feed)
    count = db.sql('SELECT count(*) FROM rt_alerts').fetchone()[0]
    assert count > 0 or len(feed.entity) == 0
