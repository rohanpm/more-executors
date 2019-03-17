# more-executors

A library of composable Python executors and futures.

[![Build Status](https://circleci.com/gh/rohanpm/more-executors/tree/master.svg?style=svg)](https://circleci.com/gh/rohanpm/more-executors/tree/master)
[![Maintainability](https://api.codeclimate.com/v1/badges/ce1b17e4d606337aa8e0/maintainability)](https://codeclimate.com/github/rohanpm/more-executors/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/ce1b17e4d606337aa8e0/test_coverage)](https://codeclimate.com/github/rohanpm/more-executors/test_coverage)

- [API documentation](https://rohanpm.github.io/more-executors/)
- [Source](https://github.com/rohanpm/more-executors)
- [PyPI](https://pypi.python.org/pypi/more-executors)

This library is intended for use with the
[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
module.  It includes a collection of `Executor` implementations in order to
extend the behavior of `Future` objects.

## Features

- Futures with implicit retry
- Futures with implicit cancel on executor shutdown
- Futures with implicit cancel after timeout
- Futures with transformed output values (sync & async)
- Futures resolved by a caller-provided polling function
- Throttle the number of futures running at once
- Synchronous executor
- Bridge `concurrent.futures` with `asyncio`
- Convenience API for creating executors

See the [API documentation](https://rohanpm.github.io/more-executors/) for detailed information on usage.

## Example

This example combines the map and retry executors to create futures for
HTTP requests running concurrently, decoding JSON responses within the
future and retrying on error.

```python
import requests
from concurrent.futures import as_completed
from more_executors import Executors


def get_json(response):
    response.raise_for_status()
    return (response.url, response.json())


def fetch_urls(urls):
    # Configure an executor:
    # - run up to 4 requests concurrently, in separate threads
    # - run get_json on each response
    # - retry up to several minutes on any errors
    executor = Executors.\
        thread_pool(max_workers=4).\
        with_map(get_json).\
        with_retry()

    # Submit requests for each given URL
    futures = [executor.submit(requests.get, url)
               for url in urls]

    # Futures API works as normal; we can block on the completed
    # futures and map/retry happens implicitly
    for future in as_completed(futures):
        (url, data) = future.result()
        do_something(url, data)
```

## Development

`virtualenv` and `pip` may be used to locally install this project from
source:

```
virtualenv ~/dev/python
. ~/dev/python/bin/activate

git clone https://github.com/rohanpm/more-executors
cd more-executors

pip install --editable .
```

Autotests may be run with pytest:

```
pip install -r test-requirements.txt
py.test
```

Submit pull requests against https://github.com/rohanpm/more-executors.

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
