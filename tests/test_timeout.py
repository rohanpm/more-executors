import time

from concurrent.futures import CancelledError
from hamcrest import assert_that, equal_to, calling, raises

from more_executors import Executors
from more_executors.timeout import TimeoutExecutor


TIMEOUT = 0.02


def sleep_and_return(sleep_time, retval):
    time.sleep(sleep_time)
    return retval


def test_success():
    with TimeoutExecutor(Executors.thread_pool(), TIMEOUT) as executor:
        f = executor.submit(sleep_and_return, TIMEOUT/10, 'abc')

        # Should complete successfully
        assert_that(f.result(), equal_to('abc'))

        assert_that(f.done())
        assert_that(not f.cancelled())

        # Should remain completed successfully through the timeout
        time.sleep(TIMEOUT*2)
        assert_that(f.done())
        assert_that(not f.cancelled())


def test_cancel_pending():
    called = []

    with Executors.thread_pool(max_workers=1).with_timeout(TIMEOUT) as executor:
        f1 = executor.submit(sleep_and_return, 1.0, 'abc')
        f2 = executor.submit(called.append, True)

        # f2 should be cancelled while f1 was still running
        assert_that(calling(f2.result), raises(CancelledError))

        # And it should not have been invoked at all
        assert_that(called, equal_to([]))

        # Meanwhile, f1 was not cancelable at the timeout, so it should have
        # completed
        assert_that(f1.result(), equal_to('abc'))


def test_cancel_future_outlives_executor():
    called = []

    def get_futures(executor):
        f1 = executor.submit(sleep_and_return, 1.0, 'abc')
        f2 = executor.submit(called.append, True)
        return (f1, f2)

    (f1, f2) = get_futures(Executors.thread_pool(max_workers=1).with_timeout(0.5))

    # f2 should be cancelled while f1 was still running
    assert_that(calling(f2.result), raises(CancelledError))

    # And it should not have been invoked at all
    assert_that(called, equal_to([]))

    # Meanwhile, f1 was not cancelable at the timeout, so it should have
    # completed
    assert_that(f1.result(), equal_to('abc'))
