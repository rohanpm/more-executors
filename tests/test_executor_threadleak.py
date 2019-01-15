import threading
import gc
from functools import partial

from pytest import fixture

from more_executors._executors import Executors

from .util import assert_soon


def poll_noop(descriptors):
    for descriptor in descriptors:
        descriptor.yield_result(descriptor.result)


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


@fixture(params=['sync', 'thread_pool', 'with_retry', 'with_poll',
                 'with_throttle', 'with_poll_throttle', 'with_timeout'])
def executor_ctor(request):
    return request.getfixturevalue('ctor_' + request.param)


def thread_names():
    return set([t.name for t in threading.enumerate()])


def assert_no_extra_threads(threads_before):
    gc.collect()
    threads_after = thread_names()
    extra_threads = threads_after - threads_before
    assert extra_threads == set()


def test_no_leak_on_noop(executor_ctor):
    no_extra_threads = partial(assert_no_extra_threads, thread_names())

    executor = executor_ctor()
    del executor

    assert_soon(no_extra_threads)


def mult2(x):
    return x*2


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
