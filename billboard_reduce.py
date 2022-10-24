# See the `ExploringBillboardData.ipynb` notebook for processing details.

import argparse
import os
import pandas as pd

parser = argparse.ArgumentParser()
# Billboard CSV file is the first argument.
# `nargs='?'` makes it optional: https://stackoverflow.com/a/4480202/780425
parser.add_argument('billboard_csv', nargs='?', type=str, default='billboard.csv',
                    help='Path to input Billboard CSV file, as produced by `billboard_scrape.py`. Defaults to "billboard.csv".')
parser.add_argument('-n', '--topn', type=int, required=False, default=100,
                    help='The number of top-charting songs (unique across all years) to export for each year. Defaults to 100.')
parser.add_argument('-o', '--output', type=str, required=False, default='billboard_reduced.csv',
                    help='The name of the output CSV file (including the .csv suffix). Defaults to "billboard_reduced.csv".')
parser.add_argument('-v', '--verbose', type=bool, required=False, default=True,
                    help='Verbose logging. Defaults to true.')
args = parser.parse_args()


# Main console output helper, respecting the `--verbose` arg.
def log(message):
    if args.verbose:
        print(message)


billboard_csv = args.billboard_csv
if not os.path.isfile(billboard_csv):
    raise ValueError('Input file "{}" not found.'.format(billboard_csv))

log('Loading input file: {}'.format(billboard_csv))
df = pd.read_csv(billboard_csv, parse_dates=['date'])

columns = ['date', 'artist', 'song', 'pos', 'pos_prev', 'pos_peak', 'weeks']
if set(df.columns) != set(columns):
    raise ValueError('Expected the Billboard CSV file to have the columns {}, but found {}'.format(columns, set(df.columns)))

# Add 'year' and 'artist_song' columns to make processing easier.
log('Creating reduced dataframe...')
df['year'] = df['date'].dt.year
df.set_index('year', inplace=True)
df['artist_song'] = df['artist'] + ': ' + df['song']

# Reduce to top-N charting songs per year, remove the derived columns we added for processing, and use `filter` to reorder columns.
df = df.sort_values(['year', 'pos_peak', 'weeks'], ascending=[True, True, False]) \
    .drop_duplicates(['artist_song']) \
    .groupby(['year']).head(args.topn) \
    .reset_index().drop(columns=['artist_song', 'year']).filter(columns)

log('\nExporting reduced Billboard CSV file to {}'.format(args.output))
df.to_csv(args.output, header=True, index=False)
