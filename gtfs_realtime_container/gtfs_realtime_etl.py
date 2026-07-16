from etl_helper import *
import requests, yaml, sched, time, sys


    
scheduler = sched.scheduler(time.time, time.sleep)


def schedule_pos_ingest(n,file,db):
    """
    Ingest positional data every n minutes
    Schedules next operation before completing current to maximise consistency in timing

    Parameters
    ----------
    n: int
        Number of minutes between executions
    file: file obj
        yaml file containing api keys
    db: psycopg db obj
        transit database object to insert data 
    """
    scheduler.enter(n * 60, 0, schedule_pos_ingest, (n,file,db))    
    url = Rotated_api_link('Translink',file,'position_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_position(db, feed)

def schedule_trip_ingest(n,file,db):
    """
    Ingest trip update data every n minutes.
    Schedules next operation before completing current to maximise consistency in timing
    
    Parameters
    ----------
    n: int
         Number of minutes between executions
    file: file obj
        yaml file containing api keys
    db: psycopg db obj
        transit database object to insert data
    """
    scheduler.enter(n * 60, 0, schedule_trip_ingest, (n,file,db))
    url = Rotated_api_link('Translink',file,'trip_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_trip(db, feed)


def schedule_alert_ingest(n,file,db):
    """
    Ingest service alert data every n minutes
    schedules next operation before completing current to maximise consistency in timing

    Parameters
    ----------
    n: int
        Number of minutes between executions
    file: file obj
        yaml file containing api keys
    db: psycopg db obj
        transit database object to insert data
    """
    scheduler.enter(n * 60, 0, schedule_alert_ingest, (n,file,db))  
    url = Rotated_api_link('Translink',file,'alerts_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_alerts(db, feed)


def main():
    # Create full url from config.yaml
    with open('config/config.yaml', 'r') as file:
        config = yaml.load(file,Loader=yaml.SafeLoader)
    
    # Add api keys to config in memory only
    load_api_keys(config)

    transit_db = create_db()

    pos_ingest_time = calculate_ingest_time(config, 'position')
    trip_ingest_time = calculate_ingest_time(config, 'trip')
    alert_ingest_time = calculate_ingest_time(config, 'alerts')

    print("Position ingest time (min): ", pos_ingest_time)
    print("Trip ingest time (min): ", trip_ingest_time)
    print("Alerts ingest time (min): ", alert_ingest_time)

    scheduler.enter(0, 0, schedule_pos_ingest, (pos_ingest_time,config,transit_db))
    scheduler.enter(0, 0, schedule_trip_ingest, (trip_ingest_time,config,transit_db))
    scheduler.enter(0, 0, schedule_alert_ingest, (alert_ingest_time,config,transit_db))

    scheduler.run()
    
if __name__=='__main__':
    main()