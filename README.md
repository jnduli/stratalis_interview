# Stratalis Interview Question

## Design

Project has 2 independent phases:

- Crawling: which produces the final pages to extract data from
- Extraction: which produces individual rows to write to the final csv

I've optimized the program for IO, using asyncio python.

## Installation

```
cd /path/to/project/folder
pipx install -f .
demo --output-file /tmp/results.csv
demo --help # for more flags
```

or for development mode:

```
cd /path/to/project/folder
python -m venv .env
python -m pip install --editable ".[dev]"
pytest .
demo --output-file /tmp/results.csv
```

# Areas for Improvement

1. Add support for stronger retry mechanisms when request fail. The current
   implementation logs the failures to stderr or a provided log_file.
2. Split out the crawler and extraction phases into separate processes, with
   different inputs. This allows extraction to happen independently of crawling.
3. Use threads/multiprocessing to perform extraction on multiple processes since
   a huge chunk of parsing is CPU bound.
4. Some pages don't have the full content specified e.g. [maire de beaulieu](https://www.mon-maire.fr/maire-de-beaulieu-15), so I've chosen to default to an empty string in these instances


