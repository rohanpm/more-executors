"""These basic tests may be applied to most types of executors."""

from random import randint
from threading import RLock
from concurrent.futures import CancelledError, wait, FIRST_COMPLETED

from six.moves.queue import Queue
from hamcrest import assert_that, equal_to, calling, raises, instance_of, has_length, is_
from pytest import fixture, skip

from more_executors.retry import RetryPolicy
# This class is meant to be imported from the top-level module, but it's
# confusing the coverage report, so import it directly here.
from more_executors._executors import Executors

from .util import assert_soon

TIMEOUT = 10.0


class SimulatedError(RuntimeError):
    pass


def map_noop(value):
    # Make MapExecutor pass everything through unchanged
    return value


def poll_noop(ds):
    # Make PollExecutor pass everything through unchanged
    [d.yield_result(d.result) for d in ds]


@fixture
def retry_executor():
    return Executors.thread_pool().with_retry(RetryPolicy())


@fixture
def threadpool_executor():
    return Executors.thread_pool()


@fixture
def sync_executor():
    return Executors.sync()


@fixture
def map_executor(threadpool_executor):
    return threadpool_executor.with_map(map_noop)


@fixture
def cancel_on_shutdown_executor(threadpool_executor):
    return threadpool_executor.with_cancel_on_shutdown()


@fixture
def map_retry_executor(threadpool_executor):
    return threadpool_executor.with_retry(RetryPolicy()).with_map(map_noop)


@fixture
def retry_map_executor(threadpool_executor):
    return threadpool_executor.with_map(map_noop).with_retry(RetryPolicy())


@fixture
def timeout_executor(threadpool_executor):
    return threadpool_executor.with_timeout(60.0)


@fixture
def cancel_poll_map_retry_executor(threadpool_executor):
    return threadpool_executor.\
        with_retry(RetryPolicy()).\
        with_map(map_noop).\
        with_poll(poll_noop).\
        with_cancel_on_shutdown()


@fixture
def cancel_retry_map_poll_executor(threadpool_executor):
    return threadpool_executor.\
        with_poll(poll_noop).\
        with_map(map_noop).\
        with_retry(RetryPolicy()).\
        with_cancel_on_shutdown()


@fixture
def retry_map_poll_executor(threadpool_executor):
    return threadpool_executor.\
        with_poll(poll_noop).\
        with_map(map_noop).\
        with_retry(RetryPolicy())


def random_cancel(_value):
    """cancel function for use with poll executor which randomly decides whether
    cancel should succeed. This targets the stress test.  The point here is that
    the futures should still satisfy the invariants of the Future API regardless
    of what the cancel function does."""
    select = randint(0, 300)
    if select < 100:
        return True
    if select < 200:
        return False
    raise RuntimeError('simulated error from cancel')


@fixture
def poll_executor(threadpool_executor):
    return threadpool_executor.\
        with_poll(poll_noop,
                  random_cancel)


def everything_executor(base_executor):
    # Get ready to go *nuts*
    return base_executor.\
        with_poll(poll_noop).\
        with_map(map_noop).\
        with_retry(RetryPolicy()).\
        with_cancel_on_shutdown().\
        with_retry(RetryPolicy()).\
        with_retry(RetryPolicy()).\
        with_timeout(120.0).\
        with_poll(poll_noop).\
        with_poll(poll_noop).\
        with_cancel_on_shutdown().\
        with_map(map_noop).\
        with_timeout(180.0).\
        with_map(map_noop).\
        with_retry(RetryPolicy())


@fixture
def everything_sync_executor(sync_executor):
    return everything_executor(sync_executor)


@fixture
def everything_threadpool_executor(threadpool_executor):
    return everything_executor(threadpool_executor)


@fixture(params=['threadpool', 'retry', 'map', 'retry_map', 'map_retry', 'poll', 'retry_map_poll',
                 'sync', 'timeout', 'cancel_poll_map_retry', 'cancel_retry_map_poll',
                 'everything_sync', 'everything_threadpool'])
def any_executor(request):
    ex = request.getfixturevalue(request.param + '_executor')
    yield ex
    ex.shutdown(True)


def test_submit_results(any_executor):
    values = range(0, 1000)
    expected_results = [v*2 for v in values]

    def fn(x):
        return x*2

    futures = [any_executor.submit(fn, x) for x in values]

    for f in futures:
        assert_that(not f.cancelled())

    results = [f.result(TIMEOUT) for f in futures]
    assert_that(results, equal_to(expected_results))


def test_broken_callback(any_executor):
    values = range(0, 1000)
    expected_results = [v*2 for v in values]
    callback_calls = []

    def fn(x):
        return x*2

    def broken_callback(f):
        callback_calls.append(f)
        raise RuntimeError('simulated broken callback')

    futures = [any_executor.submit(fn, x) for x in values]
    for f in futures:
        try:
            f.add_done_callback(broken_callback)
        except RuntimeError:
            # This is allowed - if future is done already,
            # the callback was invoked directly without exception handler.
            pass

    for f in futures:
        assert_that(not f.cancelled())

    results = [f.result(TIMEOUT) for f in futures]
    assert_that(results, equal_to(expected_results))

    # assert_soon as there's no guarantee that callbacks
    # are invoked before result() returns.
    assert_soon(lambda: assert_that(callback_calls, has_length(len(futures))))

    for f in futures:
        assert_that(f in callback_calls)


def test_submit_delayed_results(any_executor, request):
    if 'sync' in request.node.name:
        skip('test not applicable with sync executor')

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

    results = [f.result(TIMEOUT) for f in futures]
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
                assert_that(not f.cancelled(), str(f))

        for f in futures:
            if f in cancelled:
                assert_that(calling(f.result).with_args(TIMEOUT), raises(CancelledError), str(f))
            else:
                result = f.result(TIMEOUT)
                assert_that(result in expected_results)
                expected_results.remove(result)


def test_blocked_cancel(any_executor, request):
    if 'sync' in request.node.name:
        skip('test not applicable with sync executor')

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
    assert_that(future.result(TIMEOUT), equal_to(123))


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
    assert_that(futures[0].result(TIMEOUT), equal_to(2))

    # Crash, via exception
    assert_that(futures[1].exception(TIMEOUT), instance_of(SimulatedError))

    # Success
    assert_that(futures[2].result(TIMEOUT), equal_to(6))

    # Crash, via result
    assert_that(calling(futures[3].result).with_args(TIMEOUT),
                raises(SimulatedError, "Simulated error on 4"))


def test_submit_staggered(any_executor, request):
    if 'sync' in request.node.name:
        skip('test not applicable with sync executor')

    for _ in range(0, 100):
        do_test_submit_staggered(any_executor)


def do_test_submit_staggered(executor):
    values = [1, 2, 3]
    expected_results = [2, 4, 6, 2, 4, 6]

    q1 = Queue()
    q2 = Queue()

    def fn(value):
        q1.get(True)
        q2.get(True)
        return value*2

    futures = [executor.submit(fn, x) for x in values]

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
    futures.extend([executor.submit(fn, x) for x in values])

    # Let a couple of futures complete
    q2.put(True)
    q2.put(True)

    (done, not_done) = wait(futures, return_when=FIRST_COMPLETED, timeout=TIMEOUT)

    # Might have received 1, or 2
    if len(done) == 1:
        (more_done, _more_not_done) = wait(not_done, return_when=FIRST_COMPLETED,
                                           timeout=TIMEOUT)
        done = done | more_done

    assert_that(done, has_length(2))
    for f in done:
        assert_that(f.done(), str(f))

    # OK, let them all finish up now
    [q1.put(None) for _ in (1, 2, 3)]
    [q2.put(None) for _ in (1, 2, 3, 4)]

    results = [f.result(TIMEOUT) for f in futures]
    assert_that(results, equal_to(expected_results))


class StressTester(object):
    FUTURES_LIMIT = 1000
    CANCELLED = object()

    def __init__(self, executor):
        self.executor = executor
        self.lock = RLock()
        self.futures = []
        self.future_idents = {}
        self.expected_results = {}
        self.idents = 0

    def next_ident(self, msg):
        with self.lock:
            self.idents = self.idents + 1
            return '%s %d' % (msg, self.idents)

    def cancel_something(self):
        # Try to pick and cancel some future
        for f in self.futures:
            if f.cancel():
                with self.lock:
                    ident = self.future_idents[f]
                    self.expected_results[ident] = self.CANCELLED
                return

    def stress_fn(self, ident, behavior):
        sub_future = None

        if len(self.futures) < self.FUTURES_LIMIT:
            sub_ident = self.next_ident('submit from [%s]' % ident)
            sub_future = self.executor.submit(self.stress_fn, sub_ident, randint(0, 3))
            self.add_future(sub_future, sub_ident)

        # Return a value
        if behavior == 0:
            with self.lock:
                assert ident not in self.expected_results
                self.expected_results[ident] = ident
            return ident

        # Raise an exception
        if behavior == 1:
            error = RuntimeError("error %s" % ident)
            with self.lock:
                assert ident not in self.expected_results
                self.expected_results[ident] = error
            raise error

        # Submit again from callback
        if behavior == 2 and sub_future:
            sub_future.add_done_callback(
                lambda f: self.stress_fn(self.next_ident('case2 from [%s]' % sub_ident), 2))
            with self.lock:
                assert ident not in self.expected_results
                self.expected_results[ident] = ident*3
            return ident*3

        if behavior == 3:
            self.cancel_something()
            with self.lock:
                self.expected_results[ident] = ident*4
            return ident*4

        self.expected_results[ident] = ident*5
        return ident*5

    def add_future(self, future, ident):
        with self.lock:
            if len(self.futures) < self.FUTURES_LIMIT:
                self.futures.append(future)
                self.future_idents[future] = ident
                return True
        future.cancel()
        return False

    def start(self):
        for _ in range(0, 200):
            value = randint(0, 3)
            ident = self.next_ident('init')
            future = self.executor.submit(self.stress_fn, ident, value)
            if not self.add_future(future, ident):
                break

    def verify(self):
        # Wait until all the expected futures have been created
        assert_soon(lambda: assert_that(len(self.futures), equal_to(self.FUTURES_LIMIT)))

        # The timeout here is so that the test fails rather than hangs forever,
        # if something goes wrong.
        (done, _not_done) = wait(self.futures, 60.0)
        assert_that(len(done), equal_to(len(self.futures)))

        for f in self.futures:
            self.verify_future(f)

    def verify_future(self, f):
        assert f.done(), str(f)
        ident = self.future_idents[f]
        assert ident in self.expected_results, "missing entry %s for future %s" % (ident, f)
        expected_result = self.expected_results[ident]

        if expected_result is self.CANCELLED:
            assert_that(f.cancelled())
        elif isinstance(expected_result, Exception):
            assert_that(f.exception(TIMEOUT), is_(expected_result))
        else:
            assert_that(f.result(TIMEOUT), equal_to(expected_result))


def test_stress(any_executor, request):
    if 'sync' in request.node.name:
        # The test as written currently will blow the stack on sync executor
        skip('test not applicable with sync executor')

    tester = StressTester(any_executor)
    tester.start()
    tester.verify()
