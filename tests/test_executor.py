"""These basic tests may be applied to most types of executors."""

from concurrent.futures import ThreadPoolExecutor, CancelledError
from hamcrest import assert_that, equal_to, calling, raises
from pytest import fixture
import time
from six.moves.queue import Queue

from more_executors.retry import RetryExecutor


@fixture
def retry_executor():
    return RetryExecutor.new_default(ThreadPoolExecutor())


@fixture
def threadpool_executor():
    return ThreadPoolExecutor()


@fixture(params=['retry', 'threadpool'])
def any_executor(request):
    ex = request.getfixturevalue(request.param + '_executor')
    yield ex
    ex.shutdown(True)


def test_submit_results(any_executor):
    values = [1, 2, 3]
    expected_results = [2, 4, 6]

    def fn(x):
        return x*2

    futures = [any_executor.submit(fn, x) for x in values]

    for f in futures:
        assert_that(not f.cancelled())

    results = [f.result() for f in futures]
    assert_that(results, equal_to(expected_results))


def assert_soon(fn):
    for _ in range(0, 100):
        try:
            fn()
            break
        except AssertionError:
            time.sleep(0.01)
    else:
        fn()


def test_submit_delayed_results(any_executor):
    values = [1, 2, 3]
    expected_results = [2, 4, 6]

    queue = Queue()

    def fn(value):
        queue.get(True)
        return value*2

    futures = [any_executor.submit(fn, x) for x in values]

    for f in futures:
        assert_that(not f.cancelled())

    # They're not guaranteed to be "running" yet, but should
    # become so soon
    assert_soon(lambda: all([f.running() for f in futures]))

    # OK, they're not done yet though.
    for f in futures:
        assert_that(not f.done())

    # Let them proceed
    queue.put(None)
    queue.put(None)
    queue.put(None)

    results = [f.result() for f in futures]
    assert_that(results, equal_to(expected_results))


def test_cancel(any_executor):
    for _ in range(0, 100):
        values = [1, 2, 3]
        expected_results = set([2, 4, 6])

        def fn(x):
            return x*2

        futures = [any_executor.submit(fn, x) for x in values]

        cancelled = []
        for f in futures:
            # There's no way we can be sure if cancel is possible.
            # We can only try...
            if f.cancel():
                cancelled.append(f)
                assert_that(f.cancelled(), str(f))
                assert_that(not f.running(), str(f))
                assert_that(f.done(), str(f))
            else:
                # If we couldn't cancel it, that ought to mean it's either
                # running or done.
                assert_that(not f.cancelled(), str(f))
                assert_that(f.running() or f.done(), str(f))

        for f in futures:
            if f in cancelled:
                assert_that(calling(f.result), raises(CancelledError), str(f))
            else:
                result = f.result()
                assert_that(result in expected_results)
                expected_results.remove(result)
