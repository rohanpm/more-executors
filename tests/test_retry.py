"""Tests of the retry behavior in RetryExecutor."""

from concurrent.futures import ThreadPoolExecutor, Future
from hamcrest import assert_that, equal_to, is_, calling, raises, all_of, instance_of, has_string
from pytest import fixture
try:
    from unittest.mock import MagicMock, call
except ImportError:
    from mock import MagicMock, call
from six.moves.queue import Queue

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


def test_fail(executor):

    calls = []

    def fn():
        calls.append(None)
        raise ValueError("error %s" % len(calls))

    done_callback = MagicMock()

    future = executor.submit(fn)
    future.add_done_callback(done_callback)

    # It should raise the exception from result()
    assert_that(calling(future.result), raises(ValueError, 'error 10'))

    # exception() should be the same
    assert_that(future.exception(), all_of(
            instance_of(ValueError),
            has_string('error 10')))

    # It should have called the done callback exactly once
    # (It could still be queued for call from another thread)
    assert_soon(lambda: done_callback.assert_called_once_with(future))


def test_cancel_delegate():

    queue = Queue(1)

    def null_submit(*args, **kwargs):
        # makes a future which will never run
        # (thus will be able to cancel)
        queue.put(None)
        return Future()

    inner = MagicMock()
    inner.submit.side_effect = null_submit

    executor = RetryExecutor.new_default(inner)

    def never_called():
        assert False, 'this should not have been called!'

    f = executor.submit(never_called)

    def recancel(future):
        # See what happens if we try to cancel it again from within
        # the callback...
        assert_that(future.cancel(), str(future))

    f.add_done_callback(recancel)

    # Wait until it was definitely submitted to inner
    queue.get(True)

    # Though it has been submitted to delegate executor,
    # the inner future is cancelable,
    # so the outer future should be as well
    assert_that(f.cancel(), str(f))

    # Should be cancelled
    assert_that(f.cancelled(), str(f))

    # Should have only submitted once
    inner.submit.assert_called_once_with(never_called)

    # Calling cancel yet again should be harmless
    assert_that(f.cancel(), str(f))
