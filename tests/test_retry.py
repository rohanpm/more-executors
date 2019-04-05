"""Tests of the retry behavior in RetryExecutor."""

from concurrent.futures import ThreadPoolExecutor, Future
from six.moves.queue import Queue

from hamcrest import assert_that, equal_to, is_, calling, raises, all_of, instance_of, has_string
from pytest import fixture
try:
    from unittest.mock import MagicMock, call
except ImportError:
    from mock import MagicMock, call

from more_executors.retry import RetryExecutor, ExceptionRetryPolicy, RetryPolicy

from .util import assert_soon


@fixture
def max_attempts():
    return 10


@fixture
def executor(max_attempts):
    policy = ExceptionRetryPolicy(
        max_attempts=max_attempts,
        exponent=2.0,
        sleep=0.001,
        max_sleep=0.010,
        exception_base=Exception,
    )
    ex = RetryExecutor(ThreadPoolExecutor(), policy)
    yield ex
    ex.shutdown(wait=True)


def test_basic_retry(executor):
    for _ in range(0, 100):
        do_test_basic_retry(executor)


def do_test_basic_retry(executor):
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
    assert_that(future.result(10), equal_to('result'))

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
    assert_that(future.exception(), all_of(instance_of(ValueError), has_string('error 10')))

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

    executor = RetryExecutor(inner)

    def never_called():
        raise AssertionError('this should not have been called!')

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


def test_order(executor):
    # Using a policy with a bigger sleep just for this test,
    # as higher sleep time is needed for non-flaky results.
    policy = ExceptionRetryPolicy(
        max_attempts=10,
        exponent=2.0,
        sleep=0.040,
        max_sleep=0.400,
        exception_base=Exception,
    )

    f1_attempt = [0]
    f2_attempt = [0]
    calls = []
    futures = []

    def f2():
        attempt = f2_attempt[0] + 1
        f2_attempt[0] = attempt

        calls.append('f2 %s' % attempt)

        if attempt < 6:
            raise ValueError("Simulated error %s" % attempt)

        return 'f2 success'

    def f1():
        attempt = f1_attempt[0] + 1
        f1_attempt[0] = attempt

        calls.append('f1 %s' % attempt)

        if attempt == 3:
            futures.append(executor.submit_retry(policy, f2))

        if attempt < 6:
            raise ValueError("Simulated error %s" % attempt)

        return 'f1 success'

    futures.append(executor.submit_retry(policy, f1))

    # Both should eventually succeed
    assert_that(futures[0].result(), equal_to('f1 success'))
    assert_that(futures[1].result(), equal_to('f2 success'))

    assert_that(calls, equal_to([
        # The calls should occur in this order.
        # Comments list the number of time units expected until
        # a function's next call.
        'f1 1',  # f1: +1
        'f1 2',  # f1: +2
        'f1 3',  # f1: +4,  f2: +0
        'f2 1',  # f1: +4,  f2: +1
        'f2 2',  # f1: +3,  f2: +2
        'f2 3',  # f1: +1,  f2: +4
        'f1 4',  # f1: +8,  f2: +3
        'f2 4',  # f1: +5,  f2: +8
        # note: f1 hits max sleep time after next attempt
        'f1 5',  # f1: +10, f2: +3
        'f2 5',  # f1: +7,  f2: +10
        'f1 6',  # f1: fin, f2: +3
        'f2 6',  # f1: fin, f2: fin
    ]))


def test_override_policy(executor):
    """Should be able to provide a custom policy by subclassing RetryPolicy."""
    class SubRetryPolicy(RetryPolicy):
        def should_retry(self, attempt, future):
            return future.result() < 3

    fn = MagicMock()
    fn.side_effect = [1, 2, 3, AssertionError("unexpected call")]

    policy = SubRetryPolicy()

    result = executor.submit_retry(policy, fn).result()
    assert_that(result, equal_to(3))
    assert_that(fn.call_count, equal_to(3))


def test_only_retry_exception_type(executor):
    policy = ExceptionRetryPolicy(
        exception_base=[RuntimeError, ValueError, ArithmeticError],
        max_attempts=10,
        max_sleep=0.01)

    errors = [ValueError('error 1'), RuntimeError('error 2'), Exception('error 3')]

    fn = MagicMock()
    fn.side_effect = errors

    future = executor.submit_retry(policy, fn)

    # It should have retried on the first two due to exception match, then failed
    assert_that(future.exception(), is_(errors[-1]))
    assert_that(fn.call_count, equal_to(len(errors)))


def test_cancel_stops_retry(executor, max_attempts):
    calls = [0, 0]
    future = []
    cancelled = [None, None]
    error = RuntimeError("Simulated error")

    def fn(idx, do_cancel):
        calls[idx] += 1
        if calls[idx] == 2 and do_cancel:
            cancelled[idx] = future[idx].cancel()
        raise error

    future.append(executor.submit(fn, idx=0, do_cancel=False))
    future.append(executor.submit(fn, idx=1, do_cancel=True))

    # Both futures should fail
    assert future[0].exception() is error
    assert future[1].exception() is error

    # future0 didn't cancel, so it should have run as many
    # times as permitted
    assert cancelled[0] is None
    assert calls[0] == max_attempts

    # future1 had cancel() called.
    # The call to cancel() failed, but it stopped any further retries.
    assert cancelled[1] is False
    assert calls[1] == 2
