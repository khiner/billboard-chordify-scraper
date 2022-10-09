import argparse
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

DATE_FORMAT = '%Y-%m-%d' # "YYYY-mm-dd" (the format the billboard top 200 expects in URLs). Date arguments must be in this format.
ONE_WEEK = timedelta(weeks=1)
ONE_YEAR = timedelta(days=395)

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
    limited_d = d if d < datetime.today() - ONE_WEEK else d - ONE_WEEK
    return limited_d - timedelta(days=((limited_d.weekday() + 2) % 7)) # `weekday()` returns 0 (Mon) - 6 (Sun)

parser = argparse.ArgumentParser()
parser.add_argument('--start', type=str, required=False, default=(date.today() - ONE_YEAR).strftime(DATE_FORMAT)) # Default to 1 year ago
parser.add_argument('--end', type=str, required=False, default=date.today().strftime(DATE_FORMAT)) # Defaults to today
parser.add_argument('--verbose', type=bool, required=False, default=True)
args = parser.parse_args()

start_date_in = validate_date(args.start)
end_date_in = validate_date(args.end)
verbose = args.verbose

# Main console output helper, respecting the `--verbose` arg.
def debug(str):
    if verbose:
        print(str)

debug('Requested dates: {} to {}'.format(format_ymd(start_date_in), format_ymd(end_date_in)))

start_date, end_date = prev_saturday(start_date_in), prev_saturday(end_date_in)
debug('Converted dates: {} to {}'.format(format_ymd(start_date), format_ymd(end_date)))

if start_date >= end_date:
    raise ValueError('Start date must be before end date')

# Fetch the Billboard-200 for the week ending on the provided date.
# Returns parsed HTML content.
# Provided date is expected to be a Saturday.
# The Billboard site seems to handle in-between dates just fine, but being save since this would indicate something is off in week-iterating.
def fetch_billboard_200_week(week_end_date):
    if week_end_date.weekday() != 5:
        raise ValueError('Attempting to fetch a Billboard-200 week using a non-Saturday date: {}'.format(week_end_date))

    url = 'https://www.billboard.com/charts/billboard-200/{}/'.format(format_ymd(week_end_date))
    debug('Fetching: {}'.format(url))
    content = requests.get(url).content
    return BeautifulSoup(content, 'html.parser')

fetching_date = start_date
while fetching_date <= end_date:
    billboard_html = fetch_billboard_200_week(fetching_date)
    debug(billboard_html)
    fetching_date += ONE_WEEK
