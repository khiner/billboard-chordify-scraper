import argparse
from datetime import datetime, date, timedelta

import pandas as pd
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

# Formats the provided `datetime.date` as "YYYY-mm-dd" (the format the billboard top 200 expects in URLs).
def format_ymd(date):
    return date.strftime(DATE_FORMAT)

# Returns the most recent Saturday relative to the provided date, as a `datetime.date` instance.
# If the provided date is less than one week ago, the previous Sat is returned (to ensure the Billboard chart for the week is available).
def prev_saturday(d):
    limited_d = d if d < datetime.today() - ONE_WEEK else d - ONE_WEEK
    return limited_d - timedelta(days=((limited_d.weekday() + 2) % 7)) # `weekday()` returns 0 (Mon) - 6 (Sun)

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--start', type=str, required=False, default=(date.today() - ONE_YEAR).strftime(DATE_FORMAT),
    help='Start date in YYYY-mm-dd format. Defaults to one year ago')
parser.add_argument('-e', '--end', type=str, required=False, default=date.today().strftime(DATE_FORMAT),
    help='End date in YYYY-mm-dd format. Defaults to the most recent saturday with a Billboard chart.')
parser.add_argument('-c', '--chart', type=str, required=False, default='100',
    help='Default to "100" for the "Hot-100" list. Other option is "200" for "Billboard-200.')
parser.add_argument('-o', '--output', type=str, required=False, default='billboard.csv',
    help='The name of the output CSV file (with a .csv suffix). Defaults to "billboard.csv"')
parser.add_argument('-v', '--verbose', type=bool, required=False, default=True,
    help='Verbose logging. Default to true.')
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

# Fetch the Billboard-100 for the week ending on the provided date.
# Returns parsed HTML content.
# Provided date is expected to be a Saturday.
# The Billboard site seems to handle in-between dates just fine, but being save since this would indicate something is off in week-iterating.
# `list` can be either '100' or '200'
def fetch_billboard_week(week_end_date, chart_type='100'):
    if '100' not in chart_type and '200' not in chart_type:
        raise ValueError('Unknown chart type: "{}". Expected "100" or "200".'.format(chart_type))
    if week_end_date.weekday() != 5:
        raise ValueError('Attempting to fetch a Billboard week using a non-Saturday date: {}'.format(week_end_date))

    url = 'https://www.billboard.com/charts/{}/{}/'.format('hot-100' if '100' in chart_type else 'billboard-200', format_ymd(week_end_date))
    debug('Fetching: {}'.format(url))
    html = requests.get(url).text
    return BeautifulSoup(html, 'html.parser')

# Returns a dict with the following attributes:
# 'date' (string): Chart date for the entry (in "YYYY-mm-dd" format)
# 'pos' (int): Position in this week's chart
# 'pos_prev' (int): Position of the song in the previous week's chart. 0 if it was not present in previous week.
# 'pos_peak' (int): Peak position of the song across all Billboard Hot-100 charts. Always present and non-0.
# 'artist' (string): Artist name
# 'song' (string): Song name
# 'weeks' (int): Number of consecutive weeks on the charts
def parse_chart_row(chart_row, chart_date):
    pos = int(chart_row['data-detail-target'])
    inner = chart_row.find_all('li', recursive=False)[-1]
    items = inner.find('ul').find_all('li')
    artist = items[0].find('span').string.strip()
    song = items[0].find('h3').string.strip()
    pos_prev = items[3].find('span').string.strip()
    pos_peak = int(items[4].find('span').string.strip())
    weeks = int(items[5].find('span').string.strip())
    return {
        'date': format_ymd(chart_date),
        'pos': pos,
        'pos_prev': 0 if '-' in pos_prev else int(pos_prev),
        'pos_peak': pos_peak,
        'artist': artist,
        'song': song,
        'weeks': weeks,
    }


all_chart_rows = []
fetching_date = start_date
while fetching_date <= end_date:
    billboard = fetch_billboard_week(fetching_date, args.chart)
    chart_rows = billboard.find_all('ul', {'class': 'o-chart-results-list-row'})
    if len(chart_rows) != 100 and len(chart_rows) != 200:
        raise ValueError('Expected 100/200 chart rows, but found: {}'.format(len(chart_rows)))

    chart_rows_parsed = [parse_chart_row(chart_row, fetching_date) for chart_row in chart_rows]
    all_chart_rows.extend(chart_rows_parsed)

    fetching_date += ONE_WEEK

df = pd.DataFrame(all_chart_rows)
df.to_csv(args.output, header=True)
