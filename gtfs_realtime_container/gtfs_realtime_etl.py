from etl_helper import *
import requests, yaml, sched, time, sys


    
scheduler = sched.scheduler(time.time, time.sleep)


def schedule_pos_ingest(n,file,db):                                      #This function was roughly based on https://stackoverflow.com/questions/50264230/how-to-schedule-different-tasks-at-different-times-in-never-ending-program
    """
    Ingest positional data every n minutes
    
    Args:
        n (int): Number of minutes between executions
        file (file obj): yaml file containing api keys
        db (psycopg db obj): transit database object to insert data 
    """
    scheduler.enter(n * 60, 0, schedule_pos_ingest, (n,file,db))    #schedules next operation before completing current to maximise consistency in timing
    url = Rotated_api_link('Translink',file,'position_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_position(db, feed)

def schedule_trip_ingest(n,file,db):                                      #This function was roughly based on https://stackoverflow.com/questions/50264230/how-to-schedule-different-tasks-at-different-times-in-never-ending-program
    """
    Ingest trip update data every n minutes
    
    Args:
        n (int): Number of minutes between executions
        file (file obj): yaml file containing api keys
        db (psycopg db obj): transit database object to insert data 
    """
    scheduler.enter(n * 60, 0, schedule_trip_ingest, (n,file,db))   #schedules next operation before completing current to maximise consistency in timing
    url = Rotated_api_link('Translink',file,'trip_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_trip(db, feed)


def schedule_alert_ingest(n,file,db):                                      #This function was roughly based on https://stackoverflow.com/questions/50264230/how-to-schedule-different-tasks-at-different-times-in-never-ending-program
    """
    Ingest service alert data every n minutes
    
    Args:
        n (int): Number of minutes between executions
        file (file obj): yaml file containing api keys
        db (psycopg db obj): transit database object to insert data 
    """
    scheduler.enter(n * 60, 0, schedule_alert_ingest, (n,file,db))  #schedules next operation before completing current to maximise consistency in timing
    url = Rotated_api_link('Translink',file,'alerts_link')
    feed = get_feed(url)
    if feed is not None:
        insert_rt_alerts(db, feed)


def main():
    #create full url from config.yaml
    with open('config/config.yaml', 'r') as file:    #TODO put link in gtfs_realtime_etl.config
        config = yaml.load(file,Loader=yaml.SafeLoader)

    transit_db = create_db(config["database"])
    
    scheduler.enter(0, 0, schedule_pos_ingest, (1,config,transit_db))
    scheduler.enter(30, 0, schedule_trip_ingest, (1,config,transit_db))
    scheduler.enter(15, 0, schedule_alert_ingest, (30,config,transit_db))

    scheduler.run()
    
if __name__=='__main__':
    main()