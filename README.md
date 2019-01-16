# more-executors

A library of composable Python executors and futures.

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

## Changelog

### v1.19.0

- Fixed TimeoutExecutor thread leak when `shutdown()` is never called
- Introduced `more_executors.futures` module for composing futures

### v1.18.0

- Reduced log verbosity
  ([#115](https://github.com/rohanpm/more-executors/issues/115))
- Fixed deadlock when awaiting a future whose executor was garbage collected
  ([#114](https://github.com/rohanpm/more-executors/issues/114))

### v1.17.0

- Exception tracebacks are now propagated correctly on python2
  via `exception_info`

### v1.16.0

- API break: removed `new_default` methods in retry module
- Minor usability improvements to retry API
- Introduced flat_bind
  ([#97](https://github.com/rohanpm/more-executors/issues/97))

### v1.15.0

- Fixed possible deadlock in CancelOnShutdownExecutor
  ([#98](https://github.com/rohanpm/more-executors/issues/98))
- Fixed `Executors.bind` with `functools.partial`
  ([#96](https://github.com/rohanpm/more-executors/issues/96))
- Fixed ThrottleExecutor thread leak when `shutdown()` is never called
  ([#93](https://github.com/rohanpm/more-executors/issues/93))

### v1.14.0

- API break: removed `Executors.wrap` class method
- Fixed thread leaks when `shutdown()` is never called
  ([#87](https://github.com/rohanpm/more-executors/issues/87))
- Refactors to avoid pylint errors from client code
  ([#86](https://github.com/rohanpm/more-executors/issues/86))

### v1.13.0

- Introduced Executors.bind

### v1.12.0

- Introduced FlatMapExecutor

### v1.11.0

- Fixed hangs on executor shutdown

### v1.10.0

- Improved RetryPolicy API
- Fixed a race condition leading to RetryExecutor hangs
- Added `logger` argument to each executor

### v1.9.0

- Introduced ThrottleExecutor

### v1.8.0

- Fixed missing long_description in package

### v1.7.0

- Revised TimeoutExecutor concept to "cancel after timeout"
- Introduced AsyncioExecutor

### v1.6.0

- Introduce TimeoutExecutor
- Use monotonic clock in RetryExecutor
- Avoid some uninterruptible sleeps on Python 2.x
- Minor improvements to logging

## License

GPLv3
