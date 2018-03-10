"""Tests of the retry behavior in RetryExecutor."""

from concurrent.futures import ThreadPoolExecutor
from hamcrest import assert_that, equal_to, is_
from pytest import fixture
try:
    from unittest.mock import MagicMock, call
except ImportError:
    from mock import MagicMock, call

from more_executors.retry import RetryExecutor, ExceptionRetryPolicy

from .util import assert_soon


@fixture
def executor():
    policy = ExceptionRetryPolicy(
        max_attempts=10,
        exponent=2.0,
        max_sleep=0.001,
        exception_base=Exception,
    )
    ex = RetryExecutor(ThreadPoolExecutor(), policy)
    yield ex
    ex.shutdown(wait=True)


def test_basic_retry(executor):
    for _ in range(0, 100):
        fn = MagicMock()
        fn.side_effect = [
            ValueError('error 1'),
            ValueError('error 2'),
            ValueError('error 3'),
            'result',
        ]

        done_callback = MagicMock()

        future = executor.submit(fn, 'a1', 'a2', kw1=1, kw2=2)
        future.add_done_callback(done_callback)

        # It should give the correct result
        assert_that(future.result(), equal_to('result'))

        # It should not have any exception
        assert_that(future.exception(), is_(None))

        # It should have called the done callback exactly once
        # (It could still be queued for call from another thread)
        assert_soon(lambda: done_callback.assert_called_once_with(future))

        # It should have called the function 4 times with
        # exactly the submitted args
        fn.assert_has_calls([
            call('a1', 'a2', kw1=1, kw2=2),
            call('a1', 'a2', kw1=1, kw2=2),
            call('a1', 'a2', kw1=1, kw2=2),
            call('a1', 'a2', kw1=1, kw2=2),
        ])
