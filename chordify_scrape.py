import argparse
import json
import logging
import os
import re
from time import sleep
import urllib.parse

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

parser = argparse.ArgumentParser()
# Billboard CSV file is the first argument.
# `nargs='?'` makes it optional: https://stackoverflow.com/a/4480202/780425
parser.add_argument('billboard_csv', nargs='?', type=str, default='billboard_reduced.csv',
                    help='Path to input Billboard CSV file, as produced by `billboard_scrape.py` followed by `billboard_reduce.py`.' +
                         ' Defaults to "billboard_reduced.csv".')
parser.add_argument('-o', '--output', type=str, required=False, default='chordify.csv',
                    help='The name of the output CSV file (including the .csv suffix). Defaults to "chordify.csv".')
parser.add_argument('-n', '--topn', type=int, required=False, default=100,
                    help='The number of songs per year for which to scrape chords, starting at the first song for each year in the provided CSV.'
                         ' To scrape chords for all songs, just pass a number greater than or equal to the max number of songs in any year.'
                         ' Defaults to 100.')
parser.add_argument('-m', '--minchords', type=int, required=False, default=8,
                    help='The minimum number of chord instances (not unique chord values!) a song must have in order to add to the dataset.'
                         ' A result with fewer chords than this limit will be skipped.'
                         ' If no results for a song meet this chord limit, the "chords" column for the song will be NaN.'
                         ' Defaults to 8.')
parser.add_argument('-v', '--verbose', type=bool, required=False, default=True, help='Verbose logging. Defaults to true.')
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

columns = {'date', 'pos', 'pos_prev', 'pos_peak', 'artist', 'song', 'weeks'}
if not columns.issubset(set(df.columns)):
    raise ValueError('Expected the Billboard CSV file to have at least columns {}, but found {}'.format(columns, set(df.columns)))

log('Creating Chrome driver...')
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--incognito')
# options.add_argument('--headless')
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

CHORDIFY_DOMAIN = 'chordify.net'
CHORDIFY_URL = 'https://' + CHORDIFY_DOMAIN
# Here's an example of setting cookies to give chordify your session info to "sign in".
# Comment out the 3 `driver...` lines below and put in your values.
# (You can find them in Chrome (go to chordify.net) -> Devtools -> Application tab -> Storage -> Cookies -> http://chordify.net)
# You'll need a premium account to get past the "You've hit your daily chord limit".
# However, I've found we can still find chords that load in the background even with that banner in the foreground, but I wouldn't trust it.
driver.get(CHORDIFY_URL)
driver.add_cookie({'name': 'session_token', 'value': '0291f0d1ec2af7a1e8024c73bb4077c14e0a7326', 'domain': CHORDIFY_DOMAIN})
driver.add_cookie({'name': 'CID', 'value': '635559f2420756.49472117', 'domain': CHORDIFY_DOMAIN, 'SameSite': 'Lax'})
log('Chrome driver created.\n')


# Extract the chord from the classes of a chord label element.
# An example class for a chord element is "chord-label label-G_min".
# Grab every non-space character immediately following 'label-'.
def find_chord(chord_label_element):
    if not chord_label_element:
        return None

    chord_label_class = ' '.join(chord_label_element['class'])  # 'class' returns a list of strings.
    match = re.search('label-(\\S+)', chord_label_class)
    return match.group(1) if match else None


# This is nasty, but can't find a better way.
# The song's key is in a "Transpose" toolbar section.
# Ideally, we'd just search for the <a> with the "Transpose" text, but that isn't working for me,
# so we look for the element with the `transpose_text` below and locate this "Transpose" element relative to it.
# Another complication is that this element appears in slightly different parts of the DOM for different songs :/
# We don't get any help from any class names or IDs nearby, since they're all obfuscated.
def find_key_element(root):
    transpose_text = 'Change the chords by transposing the key'
    key_selector = 'span > a > span > span'  # Relative to a common ancestor in both cases
    transpose_element = root.find('div', text=transpose_text)
    if transpose_element:
        return transpose_element.parent.parent.parent.select(key_selector)[0]

    transpose_element = root.find('span', text=transpose_text)
    if transpose_element:
        return transpose_element.parent.select(key_selector)[0]

    return None


# Navigate to the provided song URL and scrape the song data.
# If successful: Returns a tuple of `(key, chords)`, where `key` is a string, and `chords` is a list of strings.
# If not successful: Throws error
def get_song_data(song_url):
    log('\tNavigating to {}'.format(song_url))
    driver.get(song_url)
    log('\tWaiting for chords to appear')
    chord_labels_selector = '#chordsArea .chords .chord:not(.nolabel) .chord-label'
    WebDriverWait(driver, 8).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, chord_labels_selector)))
    # I hate waiting for an arbitrary length of time, but I've found a few chords load quickly, then the rest load shortly after.
    # There's probably another element that we can look for that only shows up on this second load, but it's tricky to test.
    sleep(2)
    root = BeautifulSoup(driver.page_source, 'html.parser')
    key_element = find_key_element(root)
    if not key_element:
        raise RuntimeError('Could not find the key element for song at: {}'.format(song_url))

    key_chord = find_chord(key_element)
    if not key_chord:
        raise RuntimeError('Could not find the key for song at: {}'.format(song_url))

    # The 'nolabel' class is used as a placeholder for every beat the chord is held.
    # The meter is based on the current bar-length selected in the UI (which we do not interact with here).
    # We only want the elements _without_ a 'nolabel' class (not retaining any duration information).
    chords_label_elements = root.select(chord_labels_selector)
    # An example class for a chord element is "chord-label label-G_min".
    # Grab every non-space character immediately following 'label-'.
    song_chords = [find_chord(element) for element in chords_label_elements]
    song_chords = [chord for chord in song_chords if chord is not None]  # Filter out any `None` values.
    if len(song_chords) == 0:
        raise RuntimeError('Found no chords for song at: {}'.format(song_url))
    return key_chord, song_chords


# This dataframe is modified, with each item getting 'key' and 'chords' columns (if it doesn't already have them).
df['year'] = df['date'].dt.year  # Temporary column.
if 'key' not in df:
    df['key'] = ''  # Each value will be a chord string
if 'chords' not in df:
    df['chords'] = ''  # Each value will be a JSON list of chords

for year, records in df.groupby('year'):
    for record_index, record in records.head(args.topn).iterrows():  # Scrape chords for the top-N songs in each year
        artist, song = record['artist'], record['song']
        if not pd.isnull(record['key']) and not pd.isnull(record['chords']) and len(json.loads(record['chords'])) >= args.minchords:
            log('{}: {} already has a key and chords. Skipping.'.format(artist, song))
            continue

        # Use `quote` to URL-encode the string.
        # `safe=''` tells it to encode '/', which is common in combo artist names (https://stackoverflow.com/a/13625238).
        search_url = CHORDIFY_URL + '/search/' + urllib.parse.quote('{} {}'.format(artist, song), safe='')
        log('Navigating to {}'.format(search_url))
        driver.get(search_url)

        # Wait for at least one result to show up.
        results_selector = 'main > div > section > a'
        try:
            WebDriverWait(driver, 20).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, results_selector)))
        except TimeoutException:
            log('Timed out waiting for search results.')

        results_html = driver.page_source
        result_elements = BeautifulSoup(results_html, 'html.parser').select(results_selector)
        for result_index, result in enumerate(result_elements):
            try:
                # Make sure the result has chords.
                # Also, sometimes the first link we find isn't actually a link?
                if not result.find('span', text='Chordified') or result['href'] == '#':
                    continue  # Skip this result.

                log('Getting result #{} for {}: {}'.format(result_index + 1, artist, song))
                key, chords = get_song_data(CHORDIFY_URL + result['href'])
                log('\tFound key and {} chords.'.format(len(chords)))
                if len(chords) < args.minchords:
                    log('\t\tConfigured minimum chords is: {}. Skipping this result.'.format(args.minchords))
                    continue

                # Modify the main dataframe, adding the found values.
                df.at[record_index, 'key'] = key
                df.at[record_index, 'chords'] = json.dumps(chords)
                break  # We successfully got the data for one of the search results. Move on to the next record.
            except TimeoutException:
                log('Timed out getting result. Trying next result.')
            except Exception:
                logging.exception('Exception getting song data:')

        if 'key' not in record or 'chords' not in record:
            log('All {} results tried for {}: {}. Continuing to the next song without adding columns.'
                .format(len(result_elements), artist, song))

    # Save the results so far after each year, to checkpoint in case something breaks.
    log('\nCheckpoint for year {}: Exporting CSV file with added "key" and "chords" columns to {}\n'.format(year, args.output))
    # Remove the temporary added 'year' column, and export to CSV.
    df['chords'].fillna('"[]"', inplace=True)
    df.drop(columns=['year']).to_csv(args.output, header=True, index=False)

log('Closing Chrome driver...')
driver.quit()
log('Chrome driver closed.')
