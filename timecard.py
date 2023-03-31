#!/usr/bin/python
'''
Timecard: Simple time card management in Python
'''
import sys
import sqlite3
import getpass
from datetime import date
from datetime import datetime


# Configure package-level arguments (not exposed in API):
self = sys.modules[__name__]
self.db = None


def require_database(func):
    '''Decorator: Ensures database connection is established prior to calling method'''
    def test_for_db(*args, **kwargs):
        if not self.db:
            raise Exception('Database connection not established')
        return func(*args, **kwargs)
    return test_for_db


def row_to_dict(row):
    '''Utility: Converts a database row into a dictionary'''
    if not row:
        return None
    return { k: row[k] for k in row.keys() }


def rows_to_dicts(rows):
    '''Utility: Converts a set of database rows to a list of dictionaries'''
    if not rows:
        return None
    return [ row_to_dict(row) for row in rows ]


def serialize(obj):
    '''Utility: overcomes limitations with JSON dumps by assigning a time format'''
    serialized = None
    if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
        serialized = obj.isoformat()
    else: # we have a decent enough method to serialize already:
        serialized = obj
    return serialized


def sqlite_ts_to_datetime(timestamp, offset_hrs=0, offset_mins=0):
    '''Utility: Converts SQLite3 timestamps to timezone aware datetimes'''
    # Note: You should be using UTC in SQLite! You will make your life
    #       very hard if you choose to use anything else, thanks to
    #       Daylight Savings Time.
    offset = offset_hrs * 100 + offset_mins
    return datetime.strptime(timestamp + f' {offset:+05}', '%Y-%m-%d %H:%M:%S %z')


def convert_record_to_datetime(record):
    '''Utility: Converts punches from SQLite3 timestamps to timezone aware datetimes'''
    convertible_fields = ['created', 'reported', 'time_in', 'time_out']
    for field in convertible_fields:
        if field in record and record[field] is not None:
            record[field] = sqlite_ts_to_datetime(record[field])
    return record


@require_database
def get_active_punch_id(timecard_id):
    '''Retrieves the most recently active punch for a specific timecard'''
    select_active_punch_id = \
    'select id from punches where timecard = ? and active = true order by time_in desc limit 1'
    result = self.db.execute(select_active_punch_id, [timecard_id]).fetchone()
    if result:
        result = result['id']
    else:
        result = None
    return result


@require_database
def get_punch(punch_id):
    '''Retrieves a singular punch by the primary key'''
    select_punch = 'select * from punches where id = ?'
    punch = self.db.execute(select_punch, [punch_id]).fetchone()
    punch = row_to_dict(punch)
    if punch is not None:
        punch = convert_record_to_datetime(punch)
    return punch


@require_database
def get_punches_by_timecard(timecard_id):
    '''Retrieves a set of punches by timecard ID'''
    select_punches = 'select * from punches where timecard = ?'
    punches = self.db.execute(select_punches, [timecard_id]).fetchall()
    punches = rows_to_dicts(punches)
    if punches is not None:
        punches = list(map(convert_record_to_datetime, punches))
    return punches


@require_database
def get_paid_punches_by_timecard(timecard_id, paid = True):
    '''Retrieves all paid punches (unpaid if paid = False) by timecard ID'''
    select_punches = 'select * from punches where timecard = ? and paid = ?'
    punches = self.db.execute(select_punches, [timecard_id, paid]).fetchall()
    punches = rows_to_dicts(punches)
    if punches is not None:
        punches = list(map(convert_record_to_datetime, punches))
    return punches


@require_database
def get_last_punch_by_timecard(timecard_id):
    '''Retrieves a set of punches by timecard ID'''
    select_punches = 'select * from punches where timecard = ? order by time_in desc limit 1'
    punch = self.db.execute(select_punches, [timecard_id]).fetchone()
    punch = row_to_dict(punch)
    if punch is not None:
        punch = convert_record_to_datetime(punch)
    return punch


@require_database
def get_completed_punches_by_timecard(timecard_id):
    '''Retrieves all completed punches by timecard ID'''
    select_punches = \
    'select * from punches where time_out is not null and active = false and timecard = ?'
    punches = self.db.execute(select_punches, [timecard_id]).fetchall()
    punches = rows_to_dicts(punches)
    if punches is not None:
        punches = list(map(convert_record_to_datetime, punches))
    return punches


# TODO: Add card_key field such that multiple timecards may be managed by the same owner.
# Use case: a lawyer at a law firm maintains multiple time records for multiple clients.
@require_database
def create_timecard(owner = None, descr = None):
    '''Creates a new timecard with optional owner and description'''
    deactivate_existing_timecards = \
    'update timecards set active = false where owner = ?'
    create_new_timecard = \
    'insert into timecards (owner, descr) values (?, ?)'
    retrieve_created_timecard = \
    'select id from timecards where owner = ? and descr = ? and active = true order by created desc'
    # Fill in some defaults:
    if not owner:
        owner = getpass.getuser()
    if not descr:
        descr = 'Week ' + str(date.today().isocalendar().week)
    #try:
    self.db.execute(deactivate_existing_timecards, [owner])
    self.db.execute(create_new_timecard, [owner, descr])
    self.db.commit()
    #except sqlite3.IntegrityError as e:
    #    if excp.args[0].startswith('UNIQUE constraint failed')
    result = self.db.execute(retrieve_created_timecard, [owner, descr]).fetchone()
    if result:
        result = result['id']
    else:
        result = None
    return result


@require_database
def finalize_timecard(timecard_id):
    '''Finalizes an existing timecard, locking in all punches'''
    deactivate_timecard = \
    'update timecards set active = false where id = ?'
    self.db.execute(deactivate_timecard, [timecard_id])
    self.db.commit()


@require_database
def mark_timecard_reported(timecard_id):
    '''Marks an existing timecard as reported'''
    deactivate_timecard = \
    'update timecards set reported = current_timestamp where id = ?'
    timecard = get_timecard(timecard_id)
    result = True
    if not timecard['active']:
        self.db.execute(deactivate_timecard, [timecard_id])
        self.db.commit()
    return result


@require_database
def get_timecard(timecard_id):
    '''Get a timecard record by its ID'''
    select_timecard = 'select * from timecards where id = ?'
    timecard = self.db.execute(select_timecard, [timecard_id]).fetchone()
    timecard = row_to_dict(timecard)
    if timecard is not None:
        timecard = convert_record_to_datetime(timecard)
    return timecard


@require_database
def get_all_timecards():
    '''Gets all active timecards'''
    select_timecards = 'select * from timecards'
    timecards = self.db.execute(select_timecards)
    timecards = rows_to_dicts(timecards)
    if timecards is not None:
        timecards = list(map(convert_record_to_datetime, timecards))
    return timecards


@require_database
def get_all_timecards_by_owner(owner):
    '''Gets all timecards associated with an owner'''
    select_timecards = 'select * from timecards where owner = ?'
    timecards = self.db.execute(select_timecards, [owner])
    timecards = rows_to_dicts(timecards)
    if timecards is not None:
        timecards = list(map(convert_record_to_datetime, timecards))
    return timecards


@require_database
def get_active_timecards(active=True):
    '''Gets all active timecards'''
    select_timecards = 'select * from timecards where active = ?'
    timecards = self.db.execute(select_timecards, [active])
    timecards = rows_to_dicts(timecards)
    if timecards is not None:
        timecards = list(map(convert_record_to_datetime, timecards))
    return timecards


@require_database
def get_active_timecards_by_owner(owner, active=True):
    '''Gets all active timecards associated with an owner'''
    select_timecards = 'select * from timecards where owner = ? and active = ?'
    timecards = self.db.execute(select_timecards, [owner, active])
    timecards = rows_to_dicts(timecards)
    if timecards is not None:
        timecards = list(map(convert_record_to_datetime, timecards))
    return timecards


@require_database
def punch_in(timecard_id, paid=True, descr=None):
    '''Records the time an employee starts their shift or other recorded time'''
    if descr is None:
        descr = 'Time Worked'
    deactivate_old_punches = \
    'update punches set active = false where timecard = ?'
    punch_timecard = \
    'insert into punches(timecard, paid, descr, time_in) values (?, ?, ?, current_timestamp)'
    self.db.execute(deactivate_old_punches, [timecard_id])
    self.db.execute(punch_timecard, [timecard_id, paid, descr])
    self.db.commit()
    return get_punch(get_active_punch_id(timecard_id))


@require_database
def punch_out(timecard_id):
    '''Records the time an employee ends their previous punch-in'''
    punch_timecard_out = \
    'update punches set time_out = current_timestamp, active = false where id = ?'
    punch_id = get_active_punch_id(timecard_id)
    if punch_id:
        self.db.execute(punch_timecard_out, [punch_id])
        self.db.commit()
    return get_punch(punch_id)


def get_paid_time_summary(timecard_id):
    '''Compiles a summary of all time worked from a specific set of timecard punches'''
    completed_punches = get_completed_punches_by_timecard(timecard_id)
    if not completed_punches:
        return None
    report = {}
    for punch in completed_punches:
        if not punch['paid']: # Lunch or break? Probably
            continue
        date_key = punch['time_in'].date().isoformat()
        hours = None
        if 'time_out' in punch and punch['time_out'] is not None:
            hours = punch['time_out'] - punch['time_in']
        else: # Whelp, didn't record the time!
            hours = punch['time_in'] - punch['time_in']
        if date_key in report:
            report[date_key]['hours'] += hours
        else:
            report[date_key] = {
                'date': punch['time_in'],
                'hours': hours
            }
    return list(report.values())


# Internal timecard schema:
@require_database
def init_tables():
    '''Creates data tables required for the timecard recorder to work'''
    query = 'select name from sqlite_master where name = ? and type = ?'
    required_tables = {
        'timecards': '''
        CREATE TABLE timecards (
            id integer primary key,
            owner varchar,
            descr varchar,
            active boolean default true,
            created timestamp default current_timestamp,
            reported timestamp
        )
        ''',
        'punches': '''
        CREATE TABLE punches (
            id integer primary key,
            timecard integer references timecards(id),
            descr varchar,
            paid boolean default true,
            active boolean default true,
            time_in timestamp,
            time_out timestamp
        )
        ''',
    }
    required_indices = {
        'timecard_owner_idx': '''
        CREATE INDEX timecard_owner_idx
        ON timecards(owner)
        ''',
        'timecard_active_owner_idx': '''
        CREATE INDEX timecard_active_owner_idx
        ON timecards(owner, active)
        ''',
        'active_punches_idx': '''
        CREATE INDEX active_punches_idx 
        ON punches(timecard, active)
        ''',
        'punches_by_timecard_idx': '''
        CREATE INDEX punches_by_timecard_idx
        ON punches(timecard)
        '''
    }
    for table_name, table_ddl in required_tables.items():
        result = self.db.execute(query, [table_name, 'table']).fetchone()
        if not result:
            self.db.execute(table_ddl)
    for index_name, index_ddl in required_indices.items():
        result = self.db.execute(query, [index_name, 'index']).fetchone()
        if not result:
            self.db.execute(index_ddl)
    self.db.commit()


def open_timecard(filename = None):
    '''Creates a SQLite database reference for time recording'''
    if filename is None:
        filename = 'timecard.db'
    self.db = sqlite3.connect(filename)
    self.db.row_factory = sqlite3.Row


def close_timecard():
    '''Disconnects the database'''
    self.db.close()


if __name__ == '__main__':
    from interface import main
    main(self)
