import duckdb
import pandas as pd
import pytest
import responses

import etl_helper
from conftest import make_alert_feed, make_position_feed, make_trip_feed


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def test_create_rt_position_schema():
    conn = duckdb.connect(':memory:')
    etl_helper.create_rt_position(conn)
    columns = {row[0] for row in conn.sql('DESCRIBE rt_position').fetchall()}
    assert columns == {'trip_id', 'start_date', 'schedule_relationship', 'route_id',
                       'direction_id', 'latitude', 'longitude', 'current_stop_sequence',
                       'current_status', 'timestamp', 'stop_id', 'vehicle_id',
                       'vehicle_label'}
    # CREATE TABLE IF NOT EXISTS: safe to call twice
    etl_helper.create_rt_position(conn)


def test_create_rt_trip_schema():
    conn = duckdb.connect(':memory:')
    etl_helper.create_rt_trip(conn)
    columns = {row[0] for row in conn.sql('DESCRIBE rt_trip').fetchall()}
    assert columns == {'trip_id', 'start_date', 'schedule_relationship', 'route_id',
                       'direction_id', 'next_stop_sequence', 'next_stop_arrival_delay',
                       'next_stop_arrival_time', 'next_stop_departure_delay',
                       'next_stop_departure_time', 'next_stop_id',
                       'next_stop_schedule_relationship', 'vehicle_id', 'vehicle_label'}
    etl_helper.create_rt_trip(conn)


def test_create_rt_alerts_schema():
    conn = duckdb.connect(':memory:')
    etl_helper.create_rt_alerts(conn)
    columns = {row[0] for row in conn.sql('DESCRIBE rt_alerts').fetchall()}
    assert columns == {'alert_id', 'active_period_start', 'active_period_end',
                       'affected_route_ids', 'affected_route_type', 'affected_stop_ids',
                       'cause', 'effect', 'description', 'severity_level'}
    etl_helper.create_rt_alerts(conn)


def test_create_db_creates_file_and_tables(tmp_path):
    db_path = str(tmp_path / 'transit.db')
    conn = etl_helper.create_db(db_path)
    try:
        tables = {row[0] for row in conn.sql('SHOW TABLES').fetchall()}
        assert {'rt_position', 'rt_trip', 'rt_alerts'} <= tables
        assert (tmp_path / 'transit.db').exists()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# insert_rt_position
# ---------------------------------------------------------------------------

def test_insert_rt_position_inserts_row(db):
    feed = make_position_feed()
    etl_helper.insert_rt_position(db, feed)

    rows = db.sql('SELECT * FROM rt_position').df()
    assert len(rows) == 1
    row = rows.iloc[0]
    assert row['trip_id'] == 'trip-1'
    assert row['route_id'] == 'route-99'
    assert pd.Timestamp(row['start_date']) == pd.Timestamp('2026-07-16')
    assert row['latitude'] == pytest.approx(49.2827, abs=1e-4)
    assert row['longitude'] == pytest.approx(-123.1207, abs=1e-4)
    assert row['stop_id'] == 'stop-42'
    assert row['vehicle_id'] == 'veh-1'
    assert row['vehicle_label'] == 'Bus 99'
    assert row['timestamp'] == pd.to_datetime(1752600000, unit='s')


def test_insert_rt_position_is_idempotent(db):
    feed = make_position_feed()
    etl_helper.insert_rt_position(db, feed)
    etl_helper.insert_rt_position(db, feed)  # same (trip_id, vehicle_id, timestamp)

    count = db.sql('SELECT count(*) FROM rt_position').fetchone()[0]
    assert count == 1  # ON CONFLICT DO NOTHING keeps the row count flat


def test_insert_rt_position_new_timestamp_adds_row(db):
    etl_helper.insert_rt_position(db, make_position_feed(timestamp=1752600000))
    etl_helper.insert_rt_position(db, make_position_feed(timestamp=1752600060))

    count = db.sql('SELECT count(*) FROM rt_position').fetchone()[0]
    assert count == 2


# ---------------------------------------------------------------------------
# insert_rt_trip
# ---------------------------------------------------------------------------

def test_insert_rt_trip_inserts_row(db):
    feed = make_trip_feed(stop_ids=('stop-1',))
    etl_helper.insert_rt_trip(db, feed)

    rows = db.sql('SELECT * FROM rt_trip').df()
    assert len(rows) == 1
    row = rows.iloc[0]
    assert row['trip_id'] == 'trip-1'
    assert row['next_stop_id'] == 'stop-1'
    assert row['next_stop_sequence'] == '1'
    assert row['next_stop_arrival_delay'] == pd.Timedelta(seconds=60)
    assert row['next_stop_arrival_time'] == pd.to_datetime(1752600300, unit='s')
    assert row['next_stop_departure_delay'] == pd.Timedelta(seconds=90)
    assert row['vehicle_id'] == 'veh-1'


def test_insert_rt_trip_only_reads_first_stop_time_update(db):
    # Documents current behavior: only stop_time_update[0] is ingested, later
    # stop time updates in the same trip update are ignored.
    feed = make_trip_feed(stop_ids=('stop-first', 'stop-second', 'stop-third'))
    etl_helper.insert_rt_trip(db, feed)

    rows = db.sql('SELECT next_stop_id FROM rt_trip').fetchall()
    assert rows == [('stop-first',)]


def test_insert_rt_trip_is_idempotent(db):
    feed = make_trip_feed()
    etl_helper.insert_rt_trip(db, feed)
    etl_helper.insert_rt_trip(db, feed)  # same (trip_id, next_stop_id, vehicle_id)

    count = db.sql('SELECT count(*) FROM rt_trip').fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# insert_rt_alerts
# ---------------------------------------------------------------------------

def test_insert_rt_alerts_inserts_row(db):
    feed = make_alert_feed()
    etl_helper.insert_rt_alerts(db, feed)

    rows = db.sql('SELECT * FROM rt_alerts').df()
    assert len(rows) == 1
    row = rows.iloc[0]
    assert row['alert_id'] == 'alert-1'
    assert row['active_period_start'] == pd.to_datetime(1752590000, unit='s')
    assert row['active_period_end'] == pd.to_datetime(1752690000, unit='s')
    assert list(row['affected_route_ids']) == ['route-1', 'route-2']
    assert list(row['affected_stop_ids']) == ['stop-1', 'stop-2']
    assert row['description'] == 'Detour on route-1 and route-2'


def test_insert_rt_alerts_null_active_period(db):
    # A zero/unset start or end should be stored as NULL via check_datetime_null
    feed = make_alert_feed(period_start=0, period_end=0)
    etl_helper.insert_rt_alerts(db, feed)

    start, end = db.sql(
        'SELECT active_period_start, active_period_end FROM rt_alerts').fetchone()
    assert start is None
    assert end is None


def test_insert_rt_alerts_is_idempotent(db):
    feed = make_alert_feed()
    etl_helper.insert_rt_alerts(db, feed)
    etl_helper.insert_rt_alerts(db, feed)  # same alert_id

    count = db.sql('SELECT count(*) FROM rt_alerts').fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# check_datetime_null
# ---------------------------------------------------------------------------

def test_check_datetime_null_returns_nat_for_falsy_input():
    assert etl_helper.check_datetime_null(0) is pd.NaT
    assert etl_helper.check_datetime_null('') is pd.NaT
    assert etl_helper.check_datetime_null(None) is pd.NaT


def test_check_datetime_null_converts_real_timestamp():
    result = etl_helper.check_datetime_null(1752600000)
    assert result == pd.Timestamp('2025-07-15 17:20:00')  # 1752600000s since epoch, UTC


# ---------------------------------------------------------------------------
# get_feed
# ---------------------------------------------------------------------------

FEED_URL = 'https://gtfsapi.translink.ca/v3/gtfsposition?apikey=test-key'


@responses.activate
def test_get_feed_parses_200_response():
    feed = make_position_feed()
    responses.get(FEED_URL, body=feed.SerializeToString(), status=200)

    result = etl_helper.get_feed(FEED_URL)

    assert result is not None
    assert len(result.entity) == 1
    assert result.entity[0].vehicle.trip.trip_id == 'trip-1'
    assert result.entity[0].vehicle.vehicle.id == 'veh-1'


@responses.activate
def test_get_feed_raises_warning_on_non_200():
    responses.get(FEED_URL, status=503)

    with pytest.raises(Warning, match='server responded with code 503'):
        etl_helper.get_feed(FEED_URL)


# ---------------------------------------------------------------------------
# Rotated_api_link
# ---------------------------------------------------------------------------

def _config(num_keys):
    cfg = {'Translink': {
        'position_link': 'https://gtfsapi.translink.ca/v3/gtfsposition?apikey=',
        'trip_link': 'https://gtfsapi.translink.ca/v3/gtfsrealtime?apikey=',
        'num_keys': num_keys,
    }}
    for i in range(num_keys):
        cfg['Translink']['api_key' + str(i)] = 'KEY' + str(i)
    return cfg


def test_rotated_api_link_builds_url():
    config = _config(1)
    url = etl_helper.Rotated_api_link('Translink', config, 'position_link')
    assert url == 'https://gtfsapi.translink.ca/v3/gtfsposition?apikey=KEY0'


def test_rotated_api_link_round_robins_across_keys():
    config = _config(3)
    keys_used = [etl_helper.Rotated_api_link('Translink', config, 'position_link')
                 .rsplit('=', 1)[1] for _ in range(7)]
    # 3 keys should cycle: KEY0, KEY1, KEY2, KEY0, ...
    assert keys_used == ['KEY0', 'KEY1', 'KEY2', 'KEY0', 'KEY1', 'KEY2', 'KEY0']


def test_rotated_api_link_single_key_never_rotates():
    config = _config(1)
    for _ in range(3):
        url = etl_helper.Rotated_api_link('Translink', config, 'trip_link')
        assert url.endswith('KEY0')
