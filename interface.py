def main(timecard):
    '''Main method'''
    timecard.open_timecard()
    timecard.init_tables()
    timecard.close_timecard()
