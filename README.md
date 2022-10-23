# billboard-chordify-scraper

Scrape chords for billboard hot-100/top-200 songs.

(Actively developing. Just the billboard side of things for now.)

## Install and run

```shell
$ pip install -r requirements.txt
$ python billboard_scrape.py # Defaults to the range [1 year ago, most recent billboard week]
```

This will create a file called `billboard.csv` with a row per-song-per-week.

### CSV output specification

The output CSV has a header row and a row per-song-per-week in the requested period.

Here are the details for each column:

Column name | Column type | Description
------------- | ------------- | -------------
date  | string | Chart date for the entry (in "YYYY-mm-dd" format)
pos  | int | Position in this week's chart
pos_prev  | int | Position of the song in the previous week's chart. 0 if it was not present in previous week.
pos_peak  | int | Peak position of the song across all Billboard Hot-100 charts. Always present and non-0.
artist  | string | Artist name
song  | string | Song name
weeks  | int | Number of consecutive weeks on the charts

### Options

Assuming the system time when running is within Sunday Oct 9, 2022.
Let's request a start-date, `2016-4-25` (which happens to be a Monday) and an explicit end-date of `2022-10-8` (yesterday, a Saturday).
The start and end dates will be rounded to the previous Saturday, which is what Billboard uses for their weekly chart end-date.
Since the requested end date is less than one week ago, results will be limited to the week ending the previous Saturday to ensure the Billboard chart is available:

```shell
$ python billboard_scrape.py --start="2016-4-25" --end="2022-10-8"
Requested dates: 2016-04-25 to 2022-10-08
Converted dates: 2016-04-23 to 2022-10-01
```

All option details:

```shell
$ python billboard_scrape.py --help
usage: billboard_scrape.py [-h] [-s START] [-e END] [-c CHART] [-o OUTPUT] [-v VERBOSE]

options:
  -h, --help            show this help message and exit
  -s START, --start START
                        Start date in YYYY-mm-dd format. Defaults to one year ago
  -e END, --end END     End date in YYYY-mm-dd format. Defaults to the most recent saturday with a Billboard chart.
  -c CHART, --chart CHART
                        Default to "100" for the "Hot-100" list. Other option is "200" for "Billboard-200".
  -o OUTPUT, --output OUTPUT
                        The name of the output CSV file (with a .csv suffix). Defaults to "billboard.csv"
  -v VERBOSE, --verbose VERBOSE
                        Verbose logging. Defaults to true.
```
