"""These basic tests may be applied to most types of executors."""

from concurrent.futures import ThreadPoolExecutor, CancelledError, wait, FIRST_COMPLETED
from hamcrest import assert_that, equal_to, calling, raises, instance_of, has_length, is_
from pytest import fixture
from six.moves.queue import Queue
from random import randint
from threading import RLock

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
                # Cancelling multiple times should be fine
                assert_that(f.cancel())
                assert_that(f.cancel())
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


def test_stress(any_executor):
    FUTURES_LIMIT = 1000

    cancelled = object()
    lock = RLock()
    futures = []
    future_idents = {}
    expected_results = {}
    idents = [0]

    def next_ident(msg):
        with lock:
            idents[0] = idents[0] + 1
            return '%s %d' % (msg, idents[0])

    def cancel_something():
        # Try to pick and cancel some future
        for f in futures:
            if f.cancel():
                with lock:
                    ident = future_idents[f]
                    expected_results[ident] = cancelled
                return

    def stress_fn(ident, behavior):
        sub_future = None

        if len(futures) < FUTURES_LIMIT:
            sub_ident = next_ident('submit from [%s]' % ident)
            sub_future = any_executor.submit(stress_fn, sub_ident, randint(0, 3))
            with lock:
                if len(futures) < FUTURES_LIMIT:
                    futures.append(sub_future)
                    future_idents[sub_future] = sub_ident
                else:
                    sub_future.cancel()

        # Return a value
        if behavior == 0:
            with lock:
                assert ident not in expected_results
                expected_results[ident] = ident
            return ident

        # Raise an exception
        if behavior == 1:
            error = RuntimeError("error %s" % ident)
            with lock:
                assert ident not in expected_results
                expected_results[ident] = error
            raise error

        # Submit again from callback
        if behavior == 2 and sub_future:
            sub_future.add_done_callback(
                lambda f: stress_fn(next_ident('case2 from [%s]' % sub_ident), 2))
            with lock:
                assert ident not in expected_results
                expected_results[ident] = ident*3
            return ident*3

        if behavior == 3:
            cancel_something()
            with lock:
                expected_results[ident] = ident*4
            return ident*4

        expected_results[ident] = ident*5
        return ident*5

    for _ in range(0, 200):
        value = randint(0, 3)
        ident = next_ident('init')
        future = any_executor.submit(stress_fn, ident, value)
        with lock:
            if len(futures) < FUTURES_LIMIT:
                futures.append(future)
                future_idents[future] = ident
            else:
                future.cancel()
                break

    # Wait until all the expected futures have been created
    assert_soon(lambda: assert_that(len(futures), equal_to(FUTURES_LIMIT)))

    # The timeout here is so that the test fails rather than hangs forever,
    # if something goes wrong.
    (done, _not_done) = wait(futures, 60.0)
    assert_that(len(done), equal_to(len(futures)))

    for f in futures:
        assert f.done(), str(f)
        ident = future_idents[f]
        assert ident in expected_results, "missing entry %s for future %s" % (ident, f)
        expected_result = expected_results[ident]

        if expected_result is cancelled:
            assert_that(f.cancelled())
        elif isinstance(expected_result, Exception):
            assert_that(f.exception(), is_(expected_result))
        else:
            assert_that(f.result(), equal_to(expected_result))
