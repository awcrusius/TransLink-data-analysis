import pandas as pd
import requests, yaml, duckdb, sys
from datetime import datetime
from google.transit import gtfs_realtime_pb2

api_modifier = 0

def check_datetime_null(input:str):
    '''
    Returns date if input is non null else returns None

    Args: 
        input(string):  Unix time or NULL like string of numbers

    Returns:
        output(string)

    '''
    if(input):
        return pd.to_datetime(input,unit = 's')
    else:
        return pd.NaT

def create_rt_position(db):
    '''
    Creates a table in the database db for GTFS realtime trip update data

    Args: 
        db: a duckdb connection object
    '''
    db.sql('''CREATE TABLE IF NOT EXISTS rt_position
            (trip_id VARCHAR,
            start_date DATE,
            schedule_relationship INTEGER,
            route_id VARCHAR,
            direction_id VARCHAR,
            latitude FLOAT,
            longitude FLOAT,
            current_stop_sequence VARCHAR,
            current_status VARCHAR,
            timestamp TIMESTAMP,
            stop_id VARCHAR,
            vehicle_id VARCHAR,
            vehicle_label VARCHAR,
            PRIMARY KEY (trip_id, vehicle_id, timestamp))
            ''')
    
def create_rt_trip(db):
    '''
    Creates a table in the database db for GTFS realtime trip update data if it does not already exist

    Args: 
        db: a duckdb connection object
    
    '''
    db.sql('''
            CREATE TABLE IF NOT EXISTS rt_trip (
                trip_id VARCHAR,
                start_date DATE,
                schedule_relationship INTEGER,
                route_id VARCHAR,
                direction_id VARCHAR,
                next_stop_sequence VARCHAR,
                next_stop_arrival_delay INTERVAL,
                next_stop_arrival_time TIMESTAMP,
                next_stop_departure_delay INTERVAL,
                next_stop_departure_time TIMESTAMP,
                next_stop_id VARCHAR,
                next_stop_schedule_relationship VARCHAR,
                vehicle_id VARCHAR,
                vehicle_label VARCHAR,
                PRIMARY KEY (trip_id, vehicle_id, next_stop_arrival_time)
            )
            ''')
    
def create_rt_alerts(db):
    '''
    Creates a table in the database db for GTFS realtime service alert data

    Args: 
        db: a duckdb connection object
    '''
    db.sql('''
            CREATE TABLE IF NOT EXISTS rt_alerts (
                alert_id VARCHAR,
                active_period_start TIMESTAMP,
                active_period_end TIMESTAMP,
                affected_route_ids VARCHAR[],
                affected_route_type VARCHAR[],
                affected_stop_ids VARCHAR[],
                cause VARCHAR,
                effect VARCHAR,
                description VARCHAR,
                severity_level VARCHAR,
                PRIMARY KEY (alert_id)
            )
            ''')
    
def insert_rt_position(db,position_feed):
    current_pos_df = pd.DataFrame()

    for entity in position_feed.entity:
        vehicle = entity.vehicle
        trip_to_append = pd.DataFrame(data = [[vehicle.trip.trip_id,
                                            pd.to_datetime(vehicle.trip.start_date, format='%Y%m%d').date(),  #convert YYYYMMDD to YYYY-MM-DD                                         
                                            vehicle.trip.schedule_relationship,
                                            vehicle.trip.route_id,
                                            vehicle.trip.direction_id,
                                            vehicle.position.latitude,
                                            vehicle.position.longitude,
                                            vehicle.current_stop_sequence,
                                            vehicle.current_status,
                                            pd.to_datetime(vehicle.timestamp, unit='s'), #convert to unix timestamp
                                            vehicle.stop_id,
                                            vehicle.vehicle.id,
                                            vehicle.vehicle.label
                                            ]],
                                    columns = ['trip_id',
                                            'start_date',
                                            'schedule_relationship',
                                            'route_id',
                                            'direction_id',
                                            'latitude',
                                            'longitude',
                                            'current_stop_sequence',
                                            'current_status',
                                            'timestamp', 
                                            'stop_id',
                                            'vehicle_id',
                                            'vehicle_label'])

        current_pos_df = pd.concat([current_pos_df,trip_to_append])
    db.sql('INSERT INTO rt_position SELECT * FROM current_pos_df ON CONFLICT DO NOTHING')
    num_inserted = db.sql("SELECT count(*) FROM rt_position").fetchall()[0][0]
    print("rt_position inserted, total length is " + str(num_inserted), file=sys.stdout)

def insert_rt_trip(db,trip_feed):
    current_trip_df = pd.DataFrame()

    for entity in trip_feed.entity:
        trip_update = entity.trip_update
        trip_to_append = pd.DataFrame(data = [[trip_update.trip.trip_id,
                                            pd.to_datetime(trip_update.trip.start_date, format='%Y%m%d').date(),  #convert YYYYMMDD to YYYY-MM-DD                                         
                                            trip_update.trip.schedule_relationship,
                                            trip_update.trip.route_id,
                                            trip_update.trip.direction_id,
                                            trip_update.stop_time_update[0].stop_sequence,
                                            pd.to_timedelta(trip_update.stop_time_update[0].arrival.delay,unit='s'),
                                            pd.to_datetime(trip_update.stop_time_update[0].arrival.time, unit='s'),
                                            pd.to_timedelta(trip_update.stop_time_update[0].departure.delay,unit='s'),
                                            pd.to_datetime(trip_update.stop_time_update[0].departure.time, unit='s'),
                                            trip_update.stop_time_update[0].stop_id,
                                            trip_update.stop_time_update[0].schedule_relationship,
                                            trip_update.vehicle.id,
                                            trip_update.vehicle.label
                                            ]],
                                    columns = ['trip_id',
                                            'start_date',
                                            'schedule_relationship',
                                            'route_id',
                                            'direction_id',
                                            'next_stop_sequence',
                                            'next_stop_arrival_delay',
                                            'next_stop_arrival_time',
                                            'next_stop_departure_delay',
                                            'next_stop_departure_time',
                                            'next_stop_id',
                                            'next_stop_schedule_relationship',
                                            'vehicle_id',
                                            'vehicle_label'])

        current_trip_df = pd.concat([current_trip_df,trip_to_append])
    db.sql('INSERT INTO rt_trip SELECT * FROM current_trip_df ON CONFLICT DO NOTHING')
    num_inserted = db.sql("SELECT count(*) FROM rt_trip").fetchall()[0][0]
    print("rt_trip inserted, total length is " + str(num_inserted), file=sys.stdout)

def insert_rt_alerts(db,alert_feed):
    current_alerts_df = pd.DataFrame()

    for entity in alert_feed.entity:
        
        listed_route_id = []
        listed_types = []
        listed_stop_ids = []
        for informed_entity in entity.alert.informed_entity:
            listed_route_id.append(informed_entity.route_id)
            listed_types.append(informed_entity.route_type)
            listed_stop_ids.append(informed_entity.stop_id)
            
        trip_to_append = pd.DataFrame(data = [[entity.id,
                                            check_datetime_null(entity.alert.active_period[0].start),                                         
                                            check_datetime_null(entity.alert.active_period[0].end),
                                            listed_route_id,
                                            listed_types,
                                            listed_stop_ids,
                                            entity.alert.cause,
                                            entity.alert.effect,
                                            entity.alert.header_text.translation[0].text,
                                            entity.alert.severity_level
                                            ]],
                                    columns=['alert_id',
                                            'active_period_start',
                                            'active_period_end',
                                            'affected_route_ids',
                                            'affected_route_type',
                                            'affected_stop_ids',
                                            'cause',
                                            'effect',
                                            'description',
                                            'severity_level'])

        current_alerts_df = pd.concat([current_alerts_df,trip_to_append])
    db.sql('INSERT INTO rt_alerts SELECT * FROM current_alerts_df ON CONFLICT DO NOTHING')
    num_inserted = db.sql("SELECT count(*) FROM rt_alerts").fetchall()[0][0]
    print("rt_alerts inserted, total length is " + str(num_inserted), file=sys.stdout)

def get_feed(url):
    now = datetime.now().strftime("%m/%d, %H:%M:%S")
    status_failure_flag = 0 # if response shows 4 failures in a row, exit
    gtfs_feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(url)
    
    if response.status_code == 200:
        gtfs_feed.ParseFromString(response.content)
        status_failure_flag = 0
        return gtfs_feed
        
    else:
        if status_failure_flag < 4:
            raise Warning('server responded with code ' + str(response.status_code) + ' in response at ' + now ) #TODO hange to docker warning
            return None
        else:
            raise SystemExit('4 consecutive failures in response at ' + now)
        
        
def Rotated_api_link(Provider,file,link_type):
    """
    Returns api link and rotates api keys every time called 
    
    Args:
        Provider (string): provider for API keys
        file (file object): file containing API keys
        link_type (string): string containing link type. options include 'trip_link','position_link','alerts_link'

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


def create_db(dir):
    '''
    Creates database at provided path if doesn't exist and creates tables if doesn't exist

    Args: 
        dir(string):  path for database file

    Returns:
        duckdb(db): database

    '''
    db = duckdb.connect(dir, config={
        'wal_autocheckpoint': '8mb',
        'memory_limit': '2GB',
    })
    create_rt_position(db)
    create_rt_trip(db)
    create_rt_alerts(db)
    return db