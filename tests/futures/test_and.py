import time
import pytest

from more_executors._executors import Executors
from more_executors.futures import f_and, f_nocancel
from .bool_utils import falsey, truthy, as_future, assert_future_equal, \
                        resolve_inputs, resolve_value
from ..util import assert_in_traceback

cases = [
    [(falsey,), falsey],
    [(truthy,), truthy],
    [(falsey, falsey), falsey],
    [(falsey, truthy), falsey],
    [(truthy, falsey), falsey],
    [(truthy, truthy), truthy],
    [(falsey, falsey, falsey), falsey],
    [(falsey, falsey, truthy), falsey],
    [(falsey, truthy, falsey), falsey],
    [(falsey, truthy, truthy), falsey],
    [(truthy, falsey, falsey), falsey],
    [(truthy, falsey, truthy), falsey],
    [(truthy, truthy, falsey), falsey],
    [(truthy, truthy, truthy), truthy],
    [(truthy, truthy, falsey, truthy), falsey],
]


@pytest.mark.parametrize('inputs, expected_result', cases)
def test_and(inputs, expected_result, falsey, truthy):
    inputs = resolve_inputs(inputs, falsey, truthy)
    expected_result = resolve_value(expected_result, falsey, truthy)

    f_inputs = [as_future(x) for x in inputs]
    future = f_and(*f_inputs)
    assert_future_equal(future, expected_result)


def test_and_order_sync():
    f_inputs = [as_future(x)
                for x in [1, 2, 3]]

    future = f_and(*f_inputs)
    assert_future_equal(future, 3)


def test_and_order_async():
    executor = Executors.thread_pool(max_workers=2)

    def delay_then(delay, value):
        time.sleep(delay)
        return value

    f_inputs = [
        executor.submit(delay_then, 0.1, 123),
        executor.submit(delay_then, 0.05, 456),
    ]

    future = f_and(*f_inputs)
    assert_future_equal(future, 123)


def test_and_cancels():
    calls = set()
    error = RuntimeError('simulated error')

    def delayed_call(delay):
        if delay is error:
            raise error
        time.sleep(delay)
        calls.add(delay)
        return delay

    executor = Executors.thread_pool(max_workers=2)
    with executor:
        futures = [executor.submit(delayed_call, x)
                   for x in (0.5, error, 0.2, 2.0, 3.0)]

        future = f_and(*futures)

        exception = future.exception()

    # error should have been propagated
    assert exception is error

    # 0.5 definitely should have been invoked
    assert 0.5 in calls

    # up to 1 more of the calls might have succeeded,
    # but we can't say which.
    # Why: because the cancels race with the thread pool,
    # once 'error' completes then f_and and the thread pool
    # are both trying to grab the next futures ASAP,
    # and either cancel or run could win.
    assert len(calls) in (1, 2)

    # This could not have been cancelled since it was
    # submitted earlier than the terminal
    assert futures[0].done()

    # The future which terminated the and()
    assert futures[1].done()

    # at least 2 of the remaining futures should have been cancelled
    assert len([f for f in futures if f.cancelled()]) >= 2


def test_and_with_nocancel():
    calls = set()
    error = RuntimeError('simulated error')

    def delayed_call(delay):
        if delay is error:
            raise error
        time.sleep(delay)
        calls.add(delay)
        return delay

    executor = Executors.thread_pool(max_workers=2)

    futures = [executor.submit(delayed_call, x)
               for x in (0.5, error, 0.2, 1.1, 1.2)]

    futures = [f_nocancel(f) for f in futures]

    future = f_and(*futures)

    exception = future.exception()

    # error should have been propagated
    assert exception is error

    # nothing else has been called yet
    assert not calls

    # but if we wait on the last future...
    assert futures[-1].result() == 1.2

    # then all calls were made thanks to nocancel
    assert calls == set([0.5, 0.2, 1.1, 1.2])


def test_and_propagate_traceback():
    def inner_test_fn():
        raise RuntimeError('oops')

    def my_test_fn(inner_fn=None):
        if inner_fn:
            inner_fn()
        return True

    executor = Executors.thread_pool()
    futures = [
        executor.submit(my_test_fn),
        executor.submit(my_test_fn),
        executor.submit(my_test_fn, inner_fn=inner_test_fn),
        executor.submit(my_test_fn),
    ]
    future = f_and(*futures)
    assert_in_traceback(future, 'inner_test_fn')
