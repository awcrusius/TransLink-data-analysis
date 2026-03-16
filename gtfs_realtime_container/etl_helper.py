import pandas as pd
import requests, yaml, sys, psycopg2,time
from datetime import datetime
from google.transit import gtfs_realtime_pb2

api_modifier = 0
status_failure_flag = 0

def check_datetime_null(input:str):
    '''
    Returns date if input is non null else returns None

    Args: 
        input(string):  Unix time or NULL like string of numbers

    Returns:
        output(string) or None if null
    '''
    if input and input != 0:
        return pd.to_datetime(input, unit='s')
    else:
        return None
    
def parse_arrival_time(stop_time_update):
    try:
        t = stop_time_update.arrival.time
        if t is None or t == 0:
            return pd.Timestamp('1970-01-01')
        return pd.to_datetime(t, unit='s')
    except Exception:
        return pd.Timestamp('1970-01-01')

def create_rt_position(db):
    '''
    Creates a table in the database db for GTFS realtime trip update data if 
    not already created. Also creates index and hypertable for maximum ingestion efficiency.

    Args: 
        db: a psycopg2 connection object
    '''
    with db.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS rt_position
            (trip_id TEXT,
            start_date DATE,
            schedule_relationship TEXT,
            route_id TEXT,
            direction_id INTEGER,
            latitude FLOAT,
            longitude FLOAT,
            current_stop_sequence INTEGER,
            current_status TEXT,
            timestamp TIMESTAMP,
            stop_id TEXT,
            vehicle_id TEXT,
            vehicle_label TEXT)
            ''')
        cur.execute("""
            SELECT create_hypertable('rt_position', 'timestamp',
                chunk_time_interval => INTERVAL '24 hour',
                if_not_exists => TRUE)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rt_position_unique
            ON rt_position (trip_id, vehicle_id, timestamp)
        """)
    db.commit()

    
def create_rt_trip(db):
    '''
    Creates a table in the database db for GTFS realtime trip update data if 
    not already created. Also creates index and hypertable for maximum ingestion efficiency.

    Args: 
        db: a psycopg2 connection object
    
    '''
    with db.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS rt_trip (
            trip_id TEXT,
            start_date DATE,
            schedule_relationship TEXT,
            route_id TEXT,
            direction_id INTEGER,
            next_stop_sequence INTEGER,
            next_stop_arrival_delay INTEGER,
            next_stop_arrival_time TIMESTAMP NOT NULL,
            next_stop_departure_delay INTEGER,
            next_stop_departure_time TIMESTAMP,
            next_stop_id TEXT,
            next_stop_schedule_relationship TEXT,
            vehicle_id TEXT,
            vehicle_label TEXT
        )''')
        cur.execute("""
            SELECT create_hypertable('rt_trip', 'next_stop_arrival_time',
                chunk_time_interval => INTERVAL '24 hour',
                if_not_exists => TRUE)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rt_trip_unique
            ON rt_trip (trip_id, next_stop_id, vehicle_id, next_stop_arrival_time)
        """)
    db.commit()
    
def create_rt_alerts(db):
    '''
    Creates a table in the database db for GTFS realtime service alert data if 
    not already created. Also creates index and hypertable for maximum ingestion efficiency.

    Args: 
        db: a psycopg2 connection object
    '''

    with db.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS rt_alerts (
            alert_id TEXT,
            active_period_start TIMESTAMP NOT NULL,
            active_period_end TIMESTAMP,
            affected_route_ids TEXT[],
            affected_route_type TEXT[],
            affected_stop_ids TEXT[],
            cause TEXT,
            effect TEXT,
            description TEXT,
            severity_level TEXT
        )''')
        cur.execute("""
            SELECT create_hypertable('rt_alerts', 'active_period_start',
                chunk_time_interval => INTERVAL '7 days',
                if_not_exists => TRUE)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rt_alerts_unique
            ON rt_alerts (alert_id, active_period_start)
        """)
    db.commit()
    
def insert_rt_position(db,position_feed):
    rows = []
    for entity in position_feed.entity:
        vehicle = entity.vehicle
        rows.append((
            vehicle.trip.trip_id,
            pd.to_datetime(vehicle.trip.start_date, format='%Y%m%d').date(),
            gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship.Name( # type: ignore
                vehicle.trip.schedule_relationship), 
            vehicle.trip.route_id,
            vehicle.trip.direction_id,
            vehicle.position.latitude,
            vehicle.position.longitude,
            vehicle.current_stop_sequence,
            gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(   # type: ignore
                vehicle.current_status),
            pd.to_datetime(vehicle.timestamp, unit='s'),
            vehicle.stop_id,
            vehicle.vehicle.id,
            vehicle.vehicle.label
        ))

    try:
        with db.cursor() as cur:
            cur.executemany("""
                INSERT INTO rt_position (
                    trip_id, start_date, schedule_relationship, route_id, direction_id,
                    latitude, longitude, current_stop_sequence, current_status,
                    timestamp, stop_id, vehicle_id, vehicle_label
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trip_id, vehicle_id, timestamp) DO NOTHING
            """, rows)
            print(f"rt_position: {cur.rowcount} rows inserted", file=sys.stdout)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"insert_rt_position failed: {e}", file=sys.stdout)

def insert_rt_trip(db,trip_feed):
    rows = []
    for entity in trip_feed.entity:
        trip_update = entity.trip_update
        stop = trip_update.stop_time_update[0]
        rows.append((
            trip_update.trip.trip_id,
            pd.to_datetime(trip_update.trip.start_date, format='%Y%m%d').date(),
            gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship.Name( # type: ignore
                trip_update.trip.schedule_relationship),
            trip_update.trip.route_id,
            trip_update.trip.direction_id,
            stop.stop_sequence,
            stop.arrival.delay,
            parse_arrival_time(stop),
            stop.departure.delay,
            pd.to_datetime(stop.departure.time, unit='s') if stop.departure.time else None,
            stop.stop_id,
            gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship.Name(  # type: ignore
                stop.schedule_relationship),
            trip_update.vehicle.id,
            trip_update.vehicle.label
        ))

    try:
        with db.cursor() as cur:
            cur.executemany("""
                INSERT INTO rt_trip (
                    trip_id, start_date, schedule_relationship, route_id, direction_id,
                    next_stop_sequence, next_stop_arrival_delay, next_stop_arrival_time,
                    next_stop_departure_delay, next_stop_departure_time, next_stop_id,
                    next_stop_schedule_relationship, vehicle_id, vehicle_label
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trip_id, next_stop_id, vehicle_id, next_stop_arrival_time) DO NOTHING
            """, rows)
            print(f"rt_trip: {cur.rowcount} rows inserted", file=sys.stdout)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"insert_rt_trip failed: {e}", file=sys.stdout)

def insert_rt_alerts(db, alert_feed):
    rows = []
    for entity in alert_feed.entity:
        listed_route_ids = []
        listed_types = []
        listed_stop_ids = []
        for informed_entity in entity.alert.informed_entity:
            listed_route_ids.append(informed_entity.route_id)
            listed_types.append(str(informed_entity.route_type))
            listed_stop_ids.append(informed_entity.stop_id)

        rows.append((
            entity.id,
            check_datetime_null(entity.alert.active_period[0].start),
            check_datetime_null(entity.alert.active_period[0].end),
            listed_route_ids,
            listed_types,
            listed_stop_ids,
            gtfs_realtime_pb2.Alert.Cause.Name(entity.alert.cause), # type: ignore
            gtfs_realtime_pb2.Alert.Effect.Name(entity.alert.effect), # type: ignore
            entity.alert.header_text.translation[0].text,
            gtfs_realtime_pb2.Alert.SeverityLevel.Name(entity.alert.severity_level) # type: ignore
        ))

    try:
        with db.cursor() as cur:
            cur.executemany("""
                INSERT INTO rt_alerts (
                    alert_id, active_period_start, active_period_end,
                    affected_route_ids, affected_route_type, affected_stop_ids,
                    cause, effect, description, severity_level
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (alert_id, active_period_start) DO NOTHING
            """, rows)
            print(f"rt_alerts: {cur.rowcount} rows inserted", file=sys.stdout)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"insert_rt_alerts failed: {e}", file=sys.stdout)

def get_feed(url):
    global status_failure_flag
    now = datetime.now().strftime("%m/%d, %H:%M:%S")
    gtfs_feed = gtfs_realtime_pb2.FeedMessage() # type: ignore
    response = requests.get(url)
    
    if response.status_code == 200:
        gtfs_feed.ParseFromString(response.content)
        status_failure_flag = 0
        return gtfs_feed
        
    else:
        if status_failure_flag < 4:
            raise Warning('server responded with code ' + 
                          str(response.status_code) + ' '
                          'in response at ' + now ) #TODO change to send telegram message after 4 consec. failures
            return None
        else:
            raise SystemExit('4 consecutive failures in response at ' + now)
        
        
def Rotated_api_link(Provider,file,link_type):
    """
    Returns api link and rotates api keys every time called 
    
    Args:
        Provider (string): provider for API keys
        file (file object): file containing API keys
        link_type (string): string containing link type. 
        options include 'trip_link','position_link','alerts_link'

    Returns:
        URL (string): URL of desired api with rotated keys
    """
    global api_modifier

    url = file[Provider][link_type] + file[Provider]['api_key' + str(api_modifier)]
    
    if api_modifier >= file[Provider]['num_keys'] - 1:
        api_modifier = 0 

    else:
        api_modifier += 1

    return url


def create_db(dbConf):
    '''
    Creates database at provided path if doesn't exist and creates tables if doesn't exist

    Args: 
        dir(string):  path for database file
        dbConf: config.yaml object filtered for only "database" items

    Returns:
        duckdb(db): database
    '''
    for attempt in range(10):
        try:
            db = psycopg2.connect(database=dbConf["name"],
                                    user=dbConf["user"],
                                    password=dbConf["pass"],
                                    host=dbConf["host"],
                                    port=dbConf["port"])
            print("Database connected successfully")
            create_rt_position(db)
            create_rt_trip(db)
            create_rt_alerts(db)
            return db
        except:
            print(f"Could not connect to database. (attempt {attempt + 1}/10)")
            time.sleep(5)
        print("Could not connect to database after 10 attempts")
        exit(1)
