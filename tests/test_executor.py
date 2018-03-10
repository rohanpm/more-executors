"""These basic tests may be applied to most types of executors."""

from concurrent.futures import ThreadPoolExecutor, CancelledError, wait, FIRST_COMPLETED
from hamcrest import assert_that, equal_to, calling, raises, instance_of, has_length
from pytest import fixture
from six.moves.queue import Queue

from more_executors.retry import RetryExecutor, RetryPolicy

from .util import assert_soon


class SimulatedError(RuntimeError):
    pass


@fixture
def retry_executor():
    # This retry executor uses the no-op retry policy so that
    # the semantics shall match an ordinary executor.
    # Retry behavior is tested explicitly from another test.
    return RetryExecutor(ThreadPoolExecutor(), RetryPolicy())


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
    assert_soon(lambda: assert_that(all([f.running() for f in futures])))

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


def test_blocked_cancel(any_executor):
    to_fn = Queue(1)
    from_fn = Queue(1)

    def fn():
        to_fn.get()
        from_fn.put(None)
        to_fn.get()
        return 123

    future = any_executor.submit(fn)

    # Wait until fn is certainly running
    to_fn.put(None)
    from_fn.get()

    # Since the function is in progress,
    # it should NOT be possible to cancel it
    assert_that(not future.cancel(), str(future))
    assert_that(future.running(), str(future))

    to_fn.put(None)
    assert_that(future.result(), equal_to(123))


def test_submit_mixed(any_executor):
    values = [1, 2, 3, 4]

    def crash_on_even(x):
        if (x % 2) == 0:
            raise SimulatedError("Simulated error on %s" % x)
        return x*2

    futures = [any_executor.submit(crash_on_even, x) for x in values]

    for f in futures:
        assert_that(not f.cancelled())

    # Success
    assert_that(futures[0].result(), equal_to(2))

    # Crash, via exception
    assert_that(futures[1].exception(), instance_of(SimulatedError))

    # Success
    assert_that(futures[2].result(), equal_to(6))

    # Crash, via result
    assert_that(calling(futures[3].result), raises(SimulatedError, "Simulated error on 4"))


def test_submit_staggered(any_executor):
    for _ in range(0, 100):
        values = [1, 2, 3]
        expected_results = [2, 4, 6, 2, 4, 6]

        q1 = Queue()
        q2 = Queue()

        def fn(value):
            q1.get(True)
            q2.get(True)
            return value*2

        futures = [any_executor.submit(fn, x) for x in values]

        for f in futures:
            assert_that(not f.cancelled())

        # They're not guaranteed to be "running" yet, but should
        # become so soon
        assert_soon(lambda: assert_that(all([f.running() for f in futures])))

        # OK, they're not done yet though.
        for f in futures:
            assert_that(not f.done())

        # Let them proceed to first checkpoint
        [q1.put(None) for f in futures]

        # Submit some more
        futures.extend([any_executor.submit(fn, x) for x in values])

        # Let a couple of futures complete
        q2.put(True)
        q2.put(True)

        (done, not_done) = wait(futures, return_when=FIRST_COMPLETED)

        # Might have received 1, or 2
        if len(done) == 1:
            (more_done, _more_not_done) = wait(not_done, return_when=FIRST_COMPLETED)
            done = done | more_done

        assert_that(done, has_length(2))
        for f in done:
            assert_that(f.done(), str(f))

        # OK, let them all finish up now
        [q1.put(None) for _ in (1, 2, 3)]
        [q2.put(None) for _ in (1, 2, 3, 4)]

        results = [f.result() for f in futures]
        assert_that(results, equal_to(expected_results))
