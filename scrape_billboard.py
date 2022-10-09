import argparse
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

DATE_FORMAT = '%Y-%m-%d' # "YYYY-mm-dd" (the format the billboard top 200 expects in URLs). Date arguments must be in this format.

# Expects a "YYYY-mm-dd"-formatted date string, and returns the corresponding `datetime.date` object.
# Throws a `ValueError` if the provided string is not a date in the expected format.
def validate_date(date_str):
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        raise ValueError('Incorrect date format. Got: {}. Expected format: YYYY-mm-dd.'.format(date_str))

# Formats the provided `datetime.date` as "yyyy-mm-dd" (the format the billboard top 200 expects in URLs).
def format_ymd(date):
    return date.strftime(DATE_FORMAT)

# Returns the most recent Saturday relative to the provided date, as a `datetime.date` instance.
# If the provided date is less than one week ago, the previous Sat is returned (to ensure the Billboard chart for the week is available).
def prev_saturday(d):
    limited_d = d if d < datetime.today() - timedelta(days=7) else d - timedelta(days=7)
    return limited_d - timedelta(days=((limited_d.weekday() + 2) % 7)) # `weekday()` returns 0 (Mon) - 6 (Sun)
    

parser = argparse.ArgumentParser()
parser.add_argument('--start', type=str, required=False, default=(date.today() - timedelta(days=365*10)).strftime(DATE_FORMAT)) # Default to 10 years ago
parser.add_argument('--end', type=str, required=False, default=date.today().strftime(DATE_FORMAT)) # Defaults to today
args = parser.parse_args()

start_date_in = validate_date(args.start)
end_date_in = validate_date(args.end)

print('Requested dates: {} to {}'.format(format_ymd(start_date_in), format_ymd(end_date_in)))

start_date, end_date = prev_saturday(start_date_in), prev_saturday(end_date_in)
start_date_str, end_date_str = format_ymd(start_date), format_ymd(end_date)
print('Converted dates: {} to {}'.format(start_date_str, end_date_str))

if start_date >= end_date:
    raise ValueError('Start date must be before end date')

# r = requests.get(URL)
