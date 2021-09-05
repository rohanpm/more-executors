from functools import partial

from pytest import fixture

from more_executors import Executors
from more_executors._impl.event import GLOBAL_HANDLER

from .util import assert_soon, thread_names, assert_no_extra_threads


def poll_noop(descriptors):
    for descriptor in descriptors:
        descriptor.yield_result(descriptor.result)


@fixture(autouse=True)
def reset_event_handler():
    yield
    GLOBAL_HANDLER.shutdown = False


@fixture
def ctor_sync():
    return Executors.sync


@fixture
def ctor_thread_pool():
    return Executors.thread_pool


@fixture
def ctor_with_retry():
    return Executors.sync().with_retry


@fixture
def ctor_with_poll():
    def fn():
        return Executors.sync().with_poll(poll_noop)

    return fn


@fixture
def ctor_with_throttle():
    def fn():
        return Executors.sync().with_throttle(2)

    return fn


@fixture
def ctor_with_timeout():
    def fn():
        return Executors.sync().with_timeout(30.0)

    return fn


@fixture
def ctor_with_poll_throttle():
    def fn():
        return Executors.sync().with_poll(poll_noop).with_throttle(2)

    return fn


EXECUTORS_WITH_WORKER_THREAD = [
    "with_retry",
    "with_poll",
    "with_throttle",
    "with_poll_throttle",
    "with_timeout",
]


@fixture(params=["sync", "thread_pool"] + EXECUTORS_WITH_WORKER_THREAD)
def executor_ctor(request):
    return request.getfixturevalue("ctor_" + request.param)


@fixture(params=EXECUTORS_WITH_WORKER_THREAD)
def executor_with_worker_thread_ctor(request):
    return request.getfixturevalue("ctor_" + request.param)


def test_no_leak_on_noop(executor_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_ctor()
    del executor

    assert_soon(no_extra_threads)


def mult2(x):
    return x * 2


def test_no_leak_on_discarded_futures(executor_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_ctor()
    futures = [executor.submit(mult2, n) for n in range(0, 1000)]
    del executor
    del futures

    assert_soon(no_extra_threads)


def get_future_results(futures):
    return [f.result() for f in futures]


def test_no_leak_on_completed_futures(executor_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_ctor()
    results = [executor.submit(mult2, n) for n in range(0, 1000)]
    results = get_future_results(results)

    del executor

    assert_soon(no_extra_threads)


def test_no_leak_on_completed_held_futures(executor_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_ctor()
    futures = [executor.submit(mult2, n) for n in range(0, 1000)]
    get_future_results(futures)

    del executor

    assert_soon(no_extra_threads)


def test_no_leak_after_exit(executor_with_worker_thread_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_with_worker_thread_ctor()
    futures = [executor.submit(mult2, n) for n in range(0, 1000)]

    # Let at least one of them complete to guarantee that a thread has started
    # before we proceed to on_exiting().
    futures[0].result()

    GLOBAL_HANDLER.on_exiting()

    assert_soon(no_extra_threads)
