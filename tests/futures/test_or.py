import time
import logging

import pytest

from more_executors import Executors
from more_executors.futures import f_or, f_nocancel
from .bool_utils import (
    falsey,
    truthy,
    as_future,
    assert_future_equal,
    resolve_inputs,
    resolve_value,
)
from ..util import assert_in_traceback

LOG = logging.getLogger("test_or")


cases = [
    [(falsey,), falsey],
    [(truthy,), truthy],
    [(falsey, falsey), falsey],
    [(falsey, truthy), truthy],
    [(truthy, falsey), truthy],
    [(truthy, truthy), truthy],
    [(falsey, falsey, falsey), falsey],
    [(falsey, falsey, truthy), truthy],
    [(falsey, truthy, falsey), truthy],
    [(falsey, truthy, truthy), truthy],
    [(truthy, falsey, falsey), truthy],
    [(truthy, falsey, truthy), truthy],
    [(truthy, truthy, falsey), truthy],
    [(truthy, truthy, truthy), truthy],
]


@pytest.mark.parametrize("inputs, expected_result", cases)
def test_or(inputs, expected_result, falsey, truthy):
    inputs = resolve_inputs(inputs, falsey, truthy)
    expected_result = resolve_value(expected_result, falsey, truthy)

    f_inputs = [as_future(x) for x in inputs]
    future = f_or(*f_inputs)
    assert_future_equal(future, expected_result)


def test_or_order_sync(falsey):
    f_inputs = [as_future(x) for x in [falsey, 123, 456, falsey]]

    future = f_or(*f_inputs)
    assert_future_equal(future, 123)


def test_or_order_async(falsey):
    executor = Executors.thread_pool(max_workers=2)

    def delay_then(delay, value):
        time.sleep(delay)
        return value

    f_inputs = [
        as_future(falsey),
        executor.submit(delay_then, 0.1, 123),
        executor.submit(delay_then, 0.05, 456),
        as_future(falsey),
    ]

    future = f_or(*f_inputs)
    assert_future_equal(future, 456)


def test_or_cancels():
    calls = set()

    def delayed_call(delay):
        time.sleep(delay)
        calls.add(delay)
        return delay

    executor = Executors.thread_pool(max_workers=2)
    with executor:
        futures = [executor.submit(delayed_call, x) for x in (0.5, 0.1, 0.2, 2.0, 3.0)]

        future = f_or(*futures)

        result = future.result()

    # Result comes from the future which completed first
    assert result == 0.1
    assert 0.1 in calls

    # There could have been one more call, since f_or
    # cancelling other futures races with threadpool trying
    # to pick them up
    assert len(calls) in (2, 3)

    # This could not have been cancelled since it was
    # submitted earlier than the winner
    assert futures[0].done()

    # The winner 0.1
    assert futures[1].done()

    # at least 2 of the remaining futures should have been cancelled
    assert len([f for f in futures if f.cancelled()]) >= 2


def test_or_with_nocancel():
    calls = set()

    def delayed_call(delay):
        time.sleep(delay)
        calls.add(delay)
        return delay

    executor = Executors.thread_pool(max_workers=2)

    futures = [executor.submit(delayed_call, x) for x in (0.5, 0.1, 0.2, 1.0, 1.1)]

    futures = [f_nocancel(f) for f in futures]

    future = f_or(*futures)

    result = future.result()

    # Result comes from the future which completed first
    assert result == 0.1

    # Only this calls should have completed so far
    assert calls == set([0.1])

    # But if we wait on this...
    assert futures[-1].result() == 1.1

    # Then they've all completed now, thanks to nocancel
    assert calls == set([0.1, 0.2, 0.5, 1.0, 1.1])


def test_or_propagate_traceback():
    def inner_test_fn():
        raise RuntimeError("oops")

    def my_test_fn(inner_fn):
        inner_fn()

    executor = Executors.thread_pool()
    future = f_or(
        executor.submit(my_test_fn),
        executor.submit(my_test_fn),
        executor.submit(my_test_fn, inner_test_fn),
    )
    assert_in_traceback(future, "inner_test_fn")
