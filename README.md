# billboard-chordify-scraper
Scrape chords for billboard top-200 songs

## Install and run

```shell
$ pip install -r requirements.txt
$ python scrape_billboard.py # Defaults to the range [1 year ago, most recent billboard week]
```

### Using arguments

Assuming the system time when running is within Sunday Oct 9, 2022, let's request a start-date, `2016-4-25` (which happens to be a Monday) and an explicit date of `2022-10-8"` (yesterday - Saturday). The start and end dates will be rounded to the previous Saturday, which is what Billboard uses for their weekly top-200 chart end-date. Since the requested end date is less than one week ago, results will be limited to the week ending the previous Saturday to ensure the Billboard chart is available:

```shell
$ python scrape_billboard.py --start="2016-4-25" --end="2022-10-8"
Requested dates: 2016-04-25 to 2022-10-08
Converted dates: 2016-04-23 to 2022-10-01
```

