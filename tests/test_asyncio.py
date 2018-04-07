import time
import sys

import pytest
from hamcrest import assert_that, equal_to, calling, raises

from more_executors._executors import Executors


@pytest.fixture
def asyncio():
    if sys.version_info[0:2] < (3, 5):
        pytest.skip("needs python >= 3.5")
    import asyncio
    import asyncio.futures
    return asyncio


def sleep_then_return(timeout, value):
    time.sleep(timeout)
    return value


def test_run(asyncio):
    with Executors.thread_pool().with_asyncio() as executor:
        f = executor.submit(sleep_then_return, 0.01, 'abc')

        # The result should not be available yet
        assert_that(calling(f.result), raises(asyncio.futures.InvalidStateError))

        # Running in event loop should work
        result = asyncio.get_event_loop().run_until_complete(f)

    # It should have given the expected value, both from run_until_complete
    # and f.result()
    assert_that(result, equal_to('abc'))
    assert_that(result, equal_to(f.result()))


def test_with_map(asyncio):
    with Executors.thread_pool().with_map(lambda x: [x, x]).with_asyncio() as executor:
        f = executor.submit(sleep_then_return, 0.01, 'abc')

        result = asyncio.get_event_loop().run_until_complete(f)

    # MapExecutor should have worked, as usual
    assert_that(result, equal_to(['abc', 'abc']))
    assert_that(result, equal_to(f.result()))
