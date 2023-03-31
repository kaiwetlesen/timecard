'''
CLI interface library to the Timecard library
'''
import sys
from textwrap import dedent
from datetime import datetime, timezone
from getpass import getuser
from argparse import ArgumentParser

# Top box:   ┬
# Vertical box: │
# Cross box: ┼
# Horizontal box: ─


self = sys.modules[__name__]
self.parser = None
self.datetimeformat = '%B %d %Y, %I:%M:%S %p %Z'
#self.datetimeformat_short = '%m-%d-%y %I:%M:%S %p'
self.dateformat = '%B %d, %Y'
self.dateformat_short = '%m-%d-%y'
#self.timeformat = '%I:%M:%S %p'
self.timeformat_short = '%I:%M %p'


def main(timecard):
    '''Main method'''
    args = setup_parser().parse_args()
    timecard.open_timecard(args.filename)
    timecard.init_tables()
    dispatch_action(timecard, args)
    timecard.close_timecard()


def dispatch_action(timecard, args):
    '''CLI action choice dispather, runs one action chosen by the user
    Note: only one action runs at a time! Additional actions are discarded'''
    if args.new_timecard:
        perform_new_timecard(timecard, args)
    elif args.finalize_timecard:
        perform_finalize_timecard(timecard, args)
    elif args.mark_reported:
        perform_mark_reported(timecard, args)
    elif args.punch:
        perform_punch(timecard, args)
    elif args.last_punch:
        perform_get_last_punch(timecard, args)
    elif args.last_active:
        perform_get_last_active_punch(timecard, args)
    elif args.list:
        perform_list(timecard, args)
    elif args.report:
        perform_report(timecard, args)
    else:
        self.parser.print_usage()
        self.parser.exit()


def perform_new_timecard(timecard, args):
    '''Performs the new timecard action'''
    new_timecard_id = timecard.create_timecard(args.owner, args.description)
    new_timecard = timecard.get_timecard(new_timecard_id)
    print('New timecard created:')
    display_single_timecard(new_timecard)


def display_single_timecard(record):
    '''Displays a single timecard record in a tabular format'''
    #max_col_width = 35
    date = record['created'].astimezone().strftime(self.datetimeformat)
    active = 'No'
    if record['active']:
        active = 'Yes'
    print( '────────────┬───────────────────────────')
    print(f'Timecard ID │ {record["id"]}')
    print(f'Description │ {record["descr"]}')
    print(f'Owner       │ {record["owner"]}')
    print(f'Created     │ {date}')
    print(f'Active      │ {active}')


def display_single_punch(punch):
    '''Displays a single punch record in a tabular format'''
    if not punch:
        return
    pay_display = 'No'
    if punch['paid']:
        pay_display = 'Yes'
    time_in_display = punch['time_in'].astimezone().strftime(self.datetimeformat)
    print( '─────────────┬─────────────────────────────────')
    print(f' Punch ID    │ {punch["id"]}')
    print(f' Description │ {punch["descr"]}')
    print(f' Paid        │ {pay_display}')
    print(f' Time In     │ {time_in_display}')
    if punch['time_out']:
        time_out_display = punch['time_out'].astimezone().strftime(self.datetimeformat)
        print(f' Time Out    │ {time_out_display}')
    else:
        duration = datetime.now(timezone.utc) - punch['time_in']
        print(f' Duration    │ {format_duration(duration)}')


def format_duration(duration):
    '''Formats a duration in HH hrs, MM mins according to English grammar rules'''
    duration_hr =  duration.seconds // 3600
    duration_min = (duration.seconds  % 3600) // 60

    duration_display = ''
    if duration_hr == 1:
        duration_display += str(duration_hr) + ' hr, '
    else:
        duration_display += str(duration_hr) + ' hrs, '

    if duration_min == 1:
        duration_display += str(duration_min) + ' min'
    else:
        duration_display += str(duration_min) + ' mins'
    return duration_display


def display_timecard_records(records):
    '''Prints a report of provided timecard records in a tabular format'''
    if records is None or len(records) == 0:
        print('No timecards found')
        return
    print('┌──────┬───┬───────────┬─────────────────────┬──────────┬──────────┐'.center(68))
    print('│ ID # │ A │   Owner   │     Description     │ Created  │ Reported │'.center(68))
    print('│──────┼───┼───────────┼─────────────────────┼──────────┼──────────│'.center(68))
    for rec in records:
        r_id = rec['id']
        r_ac = 'Y' if rec['active'] else 'N'
        r_ow = rec['owner'][:9]
        r_ds = rec['descr'][:19]
        r_cr = rec['created'].astimezone().strftime(self.dateformat_short) \
            if rec['created'] else 'Error'
        r_rp =  rec['reported'].astimezone().strftime(self.dateformat_short) \
            if rec['reported'] else 'N/R'
        print(f'│ {r_id:^4} │ {r_ac:^1} │ {r_ow:^9} │ {r_ds:^19} │ {r_cr:^8} │ {r_rp:^8} │')
    print('└──────┴───┴───────────┴─────────────────────┴──────────┴──────────┘'.center(68))


def get_timecard_for_current_user(timecard, active=True):
    '''Retrieves any active timecards active for the current user
    Important! Will exit if no existing active timecard is found!'''
    owner = getuser()
    timecard_record = timecard.get_active_timecards_by_owner(owner, active)
    timecard_id = None
    if len(timecard_record) == 0:
        print('No ' + ('active' if active else 'inactive') + ' timecards found')
        self.parser.exit()
    else:
        timecard_id = timecard_record[0]['id']
        owner = timecard_record[0]['owner']
    return timecard_id


def select_timecard(timecard, args, active=True):
    '''Implements the timecard selection logic, prioritizing arguments over defaults'''
    timecard_id = args.timecard_number
    if timecard_id is None:
        timecard_id = get_timecard_for_current_user(timecard, active)
    return timecard_id


def perform_finalize_timecard(timecard, args):
    '''Performs the finalize timecard action'''
    timecard_id = select_timecard(timecard, args)
    timecard.finalize_timecard(timecard_id)
    print(f'Timecard {timecard_id} finalized')


def perform_mark_reported(timecard, args):
    '''Performs the mark timecard as reported action'''
    timecard_id = select_timecard(timecard, args)
    if timecard.mark_timecard_reported(timecard_id):
        print(f'Timecard {timecard_id} marked as reported')
    else:
        print(f'Timecard {timecard_id} cannot be reported, not finalized?')


def check_timecard_record(timecard, timecard_id):
    '''Logic to check that the timecard ID exists and is active'''
    timecard_record = timecard.get_timecard(timecard_id)
    if timecard_record is None:
        print(f'No such timecard {timecard_id}')
        self.parser.exit()
    elif not timecard_record['active']:
        print(f'Timecard {timecard_id} is not active')
        self.parser.exit()


def perform_punch(timecard, args):
    '''Performs the timecard punch action, displays the result'''
    punch_type = args.punch
    punch_descr = args.description
    punch_descr_display = ''
    if punch_descr:
        punch_descr_display = ' for ' + punch_descr
    punch_paid = not args.unpaid
    paid_display = ''
    if punch_paid:
        paid_display = ', paid time'
    else:
        paid_display = ', unpaid time'
    timecard_id = select_timecard(timecard, args)
    check_timecard_record(timecard, timecard_id)

    if punch_type == 'in':
        if timecard.punch_in(timecard_id, punch_paid, punch_descr):
            print(f'Punched in on timecard {timecard_id}{punch_descr_display}{paid_display}')
        else:
            print('Cannot punch in on timecard {timecard_id}')
    elif punch_type == 'out':
        if timecard.punch_out(timecard_id):
            print('Punched out on timecard {timecard_id}')
        else:
            print('Cannot punch out on timecard {timecard_id}')
    elif punch_type == 'double':
        timecard.punch_out(timecard_id)
        timecard.punch_in(timecard_id, punch_paid, punch_descr)
        print(f'Double punched on timecard {timecard_id}{punch_descr_display}{paid_display}')
    else:
        print(f'Unknown punch type: {punch_type}')


def perform_get_last_active_punch(timecard, args):
    '''Performs the get last active punch action, prints to stdout'''
    timecard_id = select_timecard(timecard, args)
    check_timecard_record(timecard, timecard_id)
    punch = timecard.get_punch(timecard.get_active_punch_id(timecard_id))
    if punch:
        print('Active Punch:')
        display_single_punch(punch)
    else:
        print('No active punch')


def perform_get_last_punch(timecard, args):
    '''Performs the get last punch action (active or not), prints to stdout'''
    timecard_id = select_timecard(timecard, args)
    check_timecard_record(timecard, timecard_id)
    punch = timecard.get_last_punch_by_timecard(timecard_id)
    if punch:
        print('Last Punch:')
        display_single_punch(punch)
    else:
        print('No punch to show')


def perform_list(timecard, args):
    '''Performs the list timecards function'''
    # TODO: make filters actually work
    if args.list:
        print('')
    records = timecard.get_all_timecards()
    display_timecard_records(records)
    # Methods:
    # - get_timecard
    # - get_all_timecards
    # - get_all_timecards_by_owner
    # - get_active_timecards (true & false)
    # - get_active_timecards_by_owner (true & false)


def perform_report(timecard, args):
    '''Performs the print report function'''
    report_type = args.report
    timecard_id = select_timecard(timecard, args, active=False)
    timecard_record = timecard.get_timecard(timecard_id)

    if report_type == 'timeworked':
        display_timecard_report_header(timecard_record)
        display_time_worked_report(timecard.get_paid_time_summary(timecard_id))
        print('───── End of Report ─────\n'.center(68))
    elif report_type == 'punches':
        display_timecard_report_header(timecard_record)
        display_punch_report(timecard.get_punches_by_timecard(timecard_id))
        print('───── End of Report ─────\n'.center(68))
    elif report_type == 'full':
        display_timecard_report_header(timecard_record)
        display_time_worked_report(timecard.get_paid_time_summary(timecard_id))
        display_punch_report(timecard.get_punches_by_timecard(timecard_id))
        print('───── End of Report ─────\n'.center(68))
    else:
        print('Unknown report type')


def display_time_worked_report(work_records):
    '''Prints out a time worked report for a given set of work records'''
    field_width = 18
    print('Time Worked'.center(68))
    print( '┌────────────────────┬────────────────────┐'.center(68))
    print( '│     Date Worked    │        Hours       │'.center(68))
    print( '│────────────────────┼────────────────────│'.center(68))
    for entry in work_records:
        date = entry['date'].astimezone().strftime(self.dateformat)
        hours = format_duration(entry['hours'])
        print(f'│ {date:^18} │ {hours:^18} │'.center(68))
    print( '└────────────────────┴────────────────────┘'.center(68))
    print('')


def display_punch_report(punch_records):
    '''Prints a report of all timecard punches'''
    # Top box:   ┬
    # Vertical box: │
    # Cross box: ┼
    # Horizontal box: ─
    print('Punch Record'.center(68))
    print( '┌──────────┬──────────┬──────────┬─────────────────────┬──────┐'.center(68))
    print( '│   Date   │ Time In  │ Time Out │     Description     │ Paid │'.center(68))
    print( '│──────────┼──────────┼──────────┼─────────────────────┼──────│'.center(68))
    seen_date = ''
    first_line = True
    for punch in punch_records:
        desc = punch['descr'][:11]
        paid = 'Yes' if punch['paid'] else 'No'
        t_in = punch['time_in'].astimezone().strftime(self.timeformat_short)
        t_out = punch['time_out'].astimezone().strftime(self.timeformat_short)
        date = punch['time_in'].astimezone().strftime(self.dateformat_short)
        if date == seen_date: # then clear it, so that we only get one date printed per day
            date = ''
        else:
            seen_date = date
            if not first_line:
                print( '│──────────┼──────────┼──────────┼─────────────────────┼──────│'.center(68))
            else:
                first_line = False;

        print(f'│ {date:^8} │ {t_in:^7} │ {t_out:^7} │ {desc:<19} │ {paid:>4} │'.center(68))
    print( '└──────────┴──────────┴──────────┴─────────────────────┴──────┘'.center(68))
    print('')


def display_timecard_report_header(record):
    '''Prints a timecard report header according to the record provided'''
    if not record['reported']:
        record['reported'] = 'Not yet reported'
    else:
        record['reported'] = record['reported'].astimezone().strftime(self.dateformat)
    if not record['created']:
        record['created'] = 'Error'
    else:
        record['created'] = record['created'].astimezone().strftime(self.dateformat)
    header_format='''
    {:^68}
    
      Timecard ID: {:<18}  Created : {:<21}
      Owner      : {:<18}  Reported: {:<21}
    
      Description: {:<51}
      {:^64}
    '''
    report_title = 'TIMECARD REPORT'
    underline = '─' * 64
    header = dedent(header_format).format(
        report_title,
        record['id'],
        record['created'],
        record['owner'],
        record['reported'],
        record['descr'],
        underline)
    print(header)


def setup_parser():
    '''Configures the options parser'''
    parser = ArgumentParser(
                description='A simple timecard application to help track the time you\'ve worked.',
                epilog='Copyright (c) Kai M Wetlesen, All Rights Reserved'
            )
    parser.add_argument('-f', '--filename', default=None)
    parser.add_argument('-d', '--description',
        help=dedent('''
        Description to add to a time punch (e.g. "Lunch", "First Break", etc.) or timecard, only
        applicable to punch ins, double punches, and creation of new timecards
        ''')
        )
    parser.add_argument('-o', '--owner', help='Select an active timecard based on owner')
    parser.add_argument('-n', '--timecard-number', help='Select a timecard by timecard number')
    #parser.add_argument('-s', '--status',
    #    choices=['a','i','f','r','active','inactive','finalized','reported'],
    #    help='Filters timecards or punches by status')

    timecard_group = parser.add_argument_group('Timecard Management',
        'Manage new and registered timecards')
    timecard_group.add_argument('-N', '--new-timecard',
        help='Creates a new timecard', action='store_true')
    timecard_group.add_argument('-F', '--finalize-timecard',
        help='Finalize the given timecard, marking it inactive', action='store_true')
    timecard_group.add_argument('-M', '--mark-reported',
        help='Marks a timecard as reported, as in the record is turned into payroll',
        action='store_true')

    punch_group = parser.add_argument_group('Time Recording', 'Punch in and out on a timecard')
    punch_group.add_argument('-P', '--punch',
        help='Punches in or out on a timecard, or double-punches to punch for break, lunch, etc.',
        choices=['in','out','double'])
    punch_group.add_argument('-G', '--last-punch', action='store_true',
        help='Show the most recent punch')
    punch_group.add_argument('-A', '--last-active', action='store_true',
        help='Show the most recent active punch')
    punch_group.add_argument('-u', '--unpaid', action='store_true', default=False,
        help=dedent(
        '''
        Indicate whether the new punch is for unpaid time (e.g. a lunch break), only applicable
        to punch ins and double punches, otherwise time is marked as paid
        ''')
        )

    reporting_group = parser.add_argument_group('Reporting',
        'Generate reports for individual timecards, find timecards, or mark timecards as reported')
    reporting_group.add_argument('-L', '--list',
        help='List either all owned, all known, all active or inactive, or all reported timecards',
        choices=['mine', 'all', 'active', 'inactive', 'reported'])
    reporting_group.add_argument('-R', '--report',
        help=dedent(
            '''
            Generate timecard reports, where "timeworked" reports only include time worked,
            "punches" only include times in and out and "full" pulls all information
            '''),
        choices=['timeworked', 'punches', 'full'])
    self.parser = parser
    return parser
