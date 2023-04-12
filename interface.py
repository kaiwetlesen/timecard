'''
Command line interface library to the Timecard library
'''
import sys
from os import getenv
from textwrap import dedent
from datetime import datetime, timezone
from getpass import getuser
from argparse import ArgumentParser


# This module ties its own parser and formats to itself for simplicity:
self = sys.modules[__name__]

# The CLI argument parser:
self.parser = None

# Various formats:
self.datetimeformat = '%B %d %Y, %I:%M:%S %p %Z'
#self.datetimeformat_short = '%m-%d-%y %I:%M:%S %p'
self.dateformat = '%B %d, %Y'
self.dateformat_short = '%m-%d-%y'
#self.timeformat = '%I:%M:%S %p'
self.timeformat_short = '%I:%M %p'

self.pagewidth = 79


def main(timecard):
    '''Main method, invoked by the timecard library'''
    args = setup_parser().parse_args()
    if args.filename:
        filename = args.filename
    elif getenv('TIMECARD_FILENAME'):
        filename = getenv('TIMECARD_FILENAME')
    else:
        filename = 'timecard.db'
    timecard.open_timecard(filename)
    timecard.init_tables()
    dispatch_action(timecard, args)
    timecard.close_timecard()


def dispatch_action(timecard, args):
    '''CLI action choice dispather, runs one action chosen by the user
    Note: only one action runs at a time! Additional actions are discarded'''
    if args.display_timecard:
        perform_display_timecard(timecard, args)
    elif args.new_timecard:
        perform_new_timecard(timecard, args)
    elif args.finalize_timecard:
        perform_finalize_timecard(timecard, args)
    elif args.mark_reported:
        perform_mark_reported(timecard, args)
    elif args.punch:
        perform_punch(timecard, args)
    elif args.time_worked:
        perform_get_time_worked(timecard, args)
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


def perform_display_timecard(timecard, args):
    '''Performs the display timecard action'''
    timecard_id = select_timecard(timecard, args)
    display_single_timecard(timecard.get_timecard(timecard_id))


def perform_new_timecard(timecard, args):
    '''Performs the new timecard action'''
    new_timecard_id = timecard.create_timecard(args.owner, args.description)
    new_timecard = timecard.get_timecard(new_timecard_id)
    print('New timecard created:')
    display_single_timecard(new_timecard)


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
            print(f'Cannot punch in on timecard {timecard_id}')
    elif punch_type == 'out':
        if timecard.punch_out(timecard_id):
            print(f'Punched out on timecard {timecard_id}')
        else:
            print(f'Cannot punch out on timecard {timecard_id}')
    elif punch_type == 'double':
        timecard.punch_out(timecard_id)
        timecard.punch_in(timecard_id, punch_paid, punch_descr)
        print(f'Double punched on timecard {timecard_id}{punch_descr_display}{paid_display}')
    else:
        print(f'Unknown punch type: {punch_type}')


def perform_get_time_worked(timecard, args):
    timecard_id = get_timecard_for_current_user(timecard)
    duration = format_duration(timecard.get_time_worked_today(timecard_id))
    duration = duration.replace('hr', 'hour').replace('min','minute').replace(',', ' and')
    print('You have worked for ' + duration + '.')


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
    # Timecard Retrieval Methods:
    # - get_timecard
    # - get_all_timecards
    # - get_all_timecards_by_owner
    # - get_active_timecards (true & false)
    # - get_active_timecards_by_owner (true & false)

    # Filtration:
    active = interpret_conditional_boolean(args.active)
    owner = args.owner
    if owner is not None and active is None:
        records = timecard.get_all_timecards_by_owner(owner)
    elif owner is None and active is not None:
        records = timecard.get_active_timecards(active)
    elif owner is not None and active is not None:
        records = timecard.get_active_timecards_by_owner(owner, active)
    else:
        records = timecard.get_all_timecards()
    display_timecard_records(records)


def perform_report(timecard, args):
    '''Performs the print report function'''
    report_type = args.report
    timecard_id = select_timecard(timecard, args)
    timecard_record = timecard.get_timecard(timecard_id)

    if report_type == 'timeworked':
        display_timecard_report_header(timecard_record)
        display_time_worked_report(timecard.get_paid_time_summary(timecard_id))
    elif report_type == 'punches':
        display_timecard_report_header(timecard_record)
        display_punch_report(timecard.get_punches_by_timecard(timecard_id))
    else:
        display_timecard_report_header(timecard_record)
        display_time_worked_report(timecard.get_paid_time_summary(timecard_id))
        display_punch_report(timecard.get_punches_by_timecard(timecard_id))
    print('<───── End of Report ─────>\n'.center(self.pagewidth))


                        ################################
                        # DISPLAY AND REPORT RENDERING #
                        ################################


def display_single_timecard(record):
    '''Displays a single timecard record in a tabular format'''
    date = record['created'].astimezone().strftime(self.datetimeformat)
    if record['reported']:
        reported = record['reported'].astimezone().strftime(self.datetimeformat)
    else:
        reported = 'Not Yet Reported'
    if record['active']:
        active = 'Yes'
    else:
        active = 'No'
    print( '────────────┬─────────────────────────────────')
    print(f'Timecard ID │ {record["id"]}')
    print(f'Description │ {record["descr"]}')
    print(f'Owner       │ {record["owner"]}')
    print(f'Active      │ {active}')
    print(f'Created     │ {date}')
    print(f'Reported    │ {reported}')


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


def display_timecard_records(records):
    '''Prints a report of provided timecard records in a tabular format'''
    if records is None or len(records) == 0:
        print('No timecards found')
        return
    print('┌──────┬───┬───────────┬─────────────────────┬──────────┬──────────┐')
    print('│ ID # │ A │   Owner   │     Description     │ Created  │ Reported │')
    print('│──────┼───┼───────────┼─────────────────────┼──────────┼──────────│')
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
    print('└──────┴───┴───────────┴─────────────────────┴──────────┴──────────┘')


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
    # lhm 2 + lh label 15 + lh field 18 + rh label 13 + rh field 20 + rhm 2 = min_width
    # Only applicable to report header, individual tables may have longer min_widths
    min_width = 68
    page_width = self.pagewidth
    half_leftover = (self.pagewidth - min_width) // 2
    # Left hand and right hand field width determination:
    lhf_width = 18 + half_leftover
    rhf_width = 20 + half_leftover
    # Description field width:
    dsf_width = self.pagewidth - 15
    # Horizontal rule width
    hr_width = self.pagewidth - 2
    # Minimum header label and whitespace dimensions:
    # >2 13                 3  10              2 <
    # >2 13                 3  10              2 <
    # >              Blank Line                  <
    # >2 13                                      <
    # >             Horizontal Rule              <
    header_format='''
    {:^{page_width}}
    {:^{page_width}}
      Timecard ID: {:<{lhf_width}}   Created : {:<{rhf_width}}
      Owner      : {:<{lhf_width}}   Reported: {:<{rhf_width}}
      Description: {:<{dsf_width}}
    {:^{page_width}}
    '''
    report_title = 'TIMECARD REPORT'
    horizontal_rule = '─' * hr_width
    header = dedent(header_format).format(
        report_title,
        horizontal_rule,
        record['id'],
        record['created'],
        record['owner'],
        record['reported'],
        record['descr'],
        horizontal_rule,
        page_width=page_width,
        lhf_width=lhf_width,
        rhf_width=rhf_width,
        dsf_width=dsf_width,
        hr_width=hr_width)
    print(header)


def display_time_worked_report(work_records):
    '''Prints out a time worked report for a given set of work records'''
    if work_records is None:
        print('[─── No Completed Time Worked ───]\n'.center(self.pagewidth))
        return
    print('[ Time Worked ]'.center(self.pagewidth))
    print( '┌────────────────────┬────────────────────┐'.center(self.pagewidth))
    print( '│     Date Worked    │        Hours       │'.center(self.pagewidth))
    print( '│────────────────────┼────────────────────│'.center(self.pagewidth))
    total = None
    for entry in work_records:
        total = total + entry['hours'] if total is not None else entry['hours']
        date = entry['date'].astimezone().strftime(self.dateformat)
        hours = format_duration(entry['hours'])
        print(f'│ {date:^18} │ {hours:^18} │'.center(self.pagewidth))
    total = format_duration(total)
    print( '│────────────────────┼────────────────────│'.center(self.pagewidth))
    print(f'│    Total Hours:    │ {total:^18} │'.center(self.pagewidth))
    print( '└────────────────────┴────────────────────┘'.center(self.pagewidth))
    print('')


def display_punch_report(punch_records):
    '''Prints a report of all timecard punches'''
    # This is a massive function that could stand for a refactor
    if punch_records is None:
        print('[── No Punches Recorded ──]\n'.center(self.pagewidth))
        return
    table_head = [ '[ Punch Record ]',
                    '┌──────────┬──────────┬──────────┬───────────┬─────────────────────┬──────┐',
                    '│   Date   │ Time In  │ Time Out │ Duration  │     Description     │ Paid │',
                    '│──────────┼──────────┼──────────┼───────────┼─────────────────────┼──────│' ]
    table_hr      = '│──────────┼──────────┼──────────┼───────────┼─────────────────────┼──────│'
    table_close   = '└──────────┴──────────┴──────────┴───────────┴─────────────────────┴──────┘'
    seen_date = ''
    first_line = True
    # Print the table header:
    for line in table_head:
        print(line.center(self.pagewidth))
    # Print the table body:
    for punch in punch_records:
        # Trim up the fields for display in the table:
        desc = punch['descr'][:19]
        paid = 'Yes' if punch['paid'] else 'No'
        t_in = punch['time_in'].astimezone().strftime(self.timeformat_short)
        # Time out may still be active if a preliminary report is generated:
        if punch['time_out']:
            t_out = punch['time_out'].astimezone().strftime(self.timeformat_short)
            dur_end = punch['time_out']
        else:
            t_out = 'N/A'
            dur_end = datetime.now(timezone.utc)
        date = punch['time_in'].astimezone().strftime(self.dateformat_short)
        # Calculate the duration for this table row:
        dur = format_duration_short((dur_end - punch['time_in']))

        # Print out a horizonal table rule followed immediately by the date
        if date != seen_date:
            seen_date = date
            if not first_line: # Prevent a double-printed HR at the top of the table
                print(table_hr.center(self.pagewidth))
            else:
                first_line = False
        else: # then clear it, so that we only get one date printed per day
            date = ''
        # Print a formatted table row:
        print(
            f'│ {date:^8} │ {t_in:^8} │ {t_out:^8} │ {dur:^9} │ {desc:^19} │ {paid:>4} │'.center(
            self.pagewidth
            )
        )
    print(table_close.center(self.pagewidth))
    print('')


                                ################
                                # PARSER SETUP #
                                ################
def setup_parser():
    '''Configures the options parser'''
    parser = ArgumentParser(
                description='A simple timecard application to help track the time you\'ve worked.',
                epilog='Copyright (c) Kai M Wetlesen, All Rights Reserved'
            )
    parser.add_argument('-f', '--filename',
        help='Database name where timecard data is stored')
    parser.add_argument('-d', '--description',
        help=dedent('''
        Description to add to a time punch (e.g. "Lunch", "First Break", etc.) or timecard, only
        applicable to punch ins, double punches, and creation of new timecards
        ''')
        )
    parser.add_argument('-o', '--owner',
        help='Select an active timecard owned by owner or create a new timecard based on owner')
    parser.add_argument('-n', '--timecard-number', help='Select a timecard by timecard number')
    parser.add_argument('-a', '--active',
        choices=['y','n','yes','no'],
        help='Filters timecards or punches by their being marked active')

    timecard_group = parser.add_argument_group('Timecard Management',
        'Manage new and registered timecards')
    timecard_group.add_argument('-D', '--display-timecard',
        help='Displays an existing timecard, selecting the most recent timecard if -n is omitted',
        action='store_true')
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
    punch_group.add_argument('-W', '--time-worked', action='store_true',
        help='Get total time worked for today')
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
        help='List timecards, optionally based on criteria established by -a and -o',
        action='store_true')
    reporting_group.add_argument('-R', '--report',
        help=dedent(
            '''
            Generate timecard reports, where "timeworked" reports only include time worked,
            "punches" only include times in and out and "full" pulls all information
            '''),
        choices=['timeworked', 'punches', 'full'])
    self.parser = parser
    return parser


                             #####################
                             # VARIOUS UTILITIES #
                             #####################


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


def check_timecard_record(timecard, timecard_id):
    '''Logic to check that the timecard ID exists and is active'''
    timecard_record = timecard.get_timecard(timecard_id)
    if timecard_record is None:
        print(f'No such timecard {timecard_id}')
        self.parser.exit()
    elif not timecard_record['active']:
        print(f'Timecard {timecard_id} is not active')
        self.parser.exit()


def interpret_conditional_boolean(value):
    '''Converts a text 'yes' or 'no' into a proper boolean, preserving unsettedness'''
    if value in ('y', 'yes'):
        active = True
    elif value in ('n', 'no'):
        active = False
    else:
        active = None
    return active


def format_duration(duration):
    '''Formats a duration in HH hrs, MM mins according to English grammar rules'''
    total_seconds = duration.days * 86400 + duration.seconds
    duration_hr =  total_seconds // 3600
    duration_min = (total_seconds  % 3600) // 60

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


def format_duration_short(duration):
    '''Formats a duration in HHh MMm for display in space constrained settings'''
    total_seconds = duration.days * 86400 + duration.seconds
    duration_hr =  total_seconds // 3600
    duration_min = (total_seconds  % 3600) // 60
    return str(duration_hr) + 'h ' + str(duration_min) + 'm'
