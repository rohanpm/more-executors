# more-executors

A library of composable Python executors.

[![Build Status](https://travis-ci.org/rohanpm/more-executors.svg?branch=master)](https://travis-ci.org/rohanpm/more-executors)
[![Coverage Status](https://coveralls.io/repos/github/rohanpm/more-executors/badge.svg?branch=master)](https://coveralls.io/github/rohanpm/more-executors?branch=master)

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
- Futures with transformed output values
- Futures resolved by a caller-provided polling function
- Synchronous executor
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

## License

GPLv3
