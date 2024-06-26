# Stratalis Interview Question

## Design

Project has 2 independent phases:

- Crawling: which produces the final pages to extract data from
- Extraction: which produces individual rows to write to the final csv

I've optimized the program for IO, using asyncio python.

## Sample Run
```
╰─$ demo --output-file /tmp/output_mayors.csv --log-level INFO
INFO:root:Started processing
INFO:root:Found a total of 7689 region listings
INFO:root:Total results to extract: 7689
INFO:root:Start extracting results for 500 pages
.
.
INFO:root:Start extracting results for 500 pages
ERROR:root:Failed to extract mayor info from CrawlResult(region='Guyane', ville='Apatou (97317)', mayor_name='M. Paul DOLIANKI', mayor_link='https://www.mon-maire.fr/maire-de-apatou-973'), errorType: <class 'aiohttp.client_exceptions.ServerDisconnectedError'>, error: Server disconnected
INFO:root:Completed processing, written 6571 rows. Took 625.9389003240003 seconds.
```

## Installation

```
cd /path/to/project/folder
pipx install -f .
# Fast run
demo --output-file /tmp/limites.csv --log-level INFO --query-limit 100
# Attempt to get full data from the website
demo --output-file /tmp/results.csv
demo --help # for more flags
```

or for development mode:

```
cd /path/to/project/folder
python -m venv .env
source .env/bin/activate
python -m pip install --editable ".[dev]"
# note you may need to deactivate and reactivate the virtual env
pytest .
demo --output-file /tmp/limites.csv --query-limit 100
```

# Areas for Improvement

1. Add support for stronger retry mechanisms when request fail. The current
   implementation logs the failures to stderr or a provided log_file.
2. Split out the crawler and extraction phases into separate processes, with
   different inputs. This allows extraction to happen independently of crawling.
3. Use threads/multiprocessing to perform extraction on multiple processes since
   a huge chunk of parsing is CPU bound.
4. Some pages don't have the full content specified e.g. [maire de
   beaulieu](https://www.mon-maire.fr/maire-de-beaulieu-15), so I've chosen to
default to an empty string in these instances
5. Some pages cannot be parsed e.g.
   [maire-de-tsingoni](https://www.mon-maire.fr/maire-de-tsingoni-976), these
   will be logged out to stderr.
6. Better handling for rate limiting from their site i.e. after ~12000 requests,
   they cause TimeOuts. You can use `--query-limit 100` to get a smaller subset


