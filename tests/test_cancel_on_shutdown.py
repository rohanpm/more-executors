from threading import Event
import time

from hamcrest import (
    assert_that,
    equal_to,
    is_in,
    calling,
    raises,
    less_than_or_equal_to,
    greater_than_or_equal_to,
)

from more_executors import Executors
from more_executors.cancel_on_shutdown import CancelOnShutdownExecutor


def test_cancels():
    proceed = Event()
    count = 1000
    running_count = 0
    canceled_count = 0
    exception_count = 0
    completed_count = 0

    futures = []

    executor = Executors.thread_pool(max_workers=2).with_cancel_on_shutdown()
    futures = [executor.submit(proceed.wait) for _ in range(0, count)]

    # I'm using wait=False here since otherwise it could block on the 2 threads
    # currently in progress to finish their work items.  I can't see a way to
    # make the test fully synchronized, and using wait=True, without deadlock.
    executor.shutdown(wait=False)

    # Now let those two threads complete (if they've started)
    proceed.set()

    # Collect status of the futures.
    for future in futures:
        if future.running():
            running_count += 1
        elif future.cancelled():
            canceled_count += 1
        elif future.exception():
            exception_count += 1
        elif future.done():
            completed_count += 1

    # No futures should have failed
    assert_that(exception_count, equal_to(0))

    # Could have been anywhere from 0..2 futures running
    assert_that(running_count, is_in((0, 1, 2)))

    # Could have been anywhere from 0..2 futures completed
    assert_that(completed_count, is_in((0, 1, 2)))

    # All others should have been cancelled
    assert_that(canceled_count, less_than_or_equal_to(count))
    assert_that(canceled_count, greater_than_or_equal_to(count - 2))

    # Harmless to call shutdown again
    executor.shutdown()


def test_submit_during_shutdown():
    proceed = Event()
    futures = []
    submit_more_done = [False]

    executor = Executors.thread_pool(max_workers=2).with_cancel_on_shutdown()
    futures = [executor.submit(proceed.wait) for _ in (1, 2, 3)]

    def submit_more(f):
        assert_that(f, equal_to(futures[2]))
        assert_that(
            calling(executor.submit).with_args(lambda: None),
            raises(RuntimeError, "cannot schedule new futures after shutdown"),
        )
        submit_more_done[0] = True

    futures[2].add_done_callback(submit_more)

    # Shut it down...
    executor.shutdown(wait=False)
    proceed.set()

    # That should have cancelled futures[2]
    assert_that(futures[2].cancelled())

    # And the tests in submit_more should have run
    assert_that(submit_more_done[0], equal_to(True))


def test_submit_during_shutdown_no_deadlock():
    proceed = Event()
    submit_more_done = [False]

    executor = CancelOnShutdownExecutor(Executors.thread_pool(max_workers=2))

    def submit_more():
        proceed.wait()
        assert_that(
            calling(executor.submit).with_args(lambda: None),
            raises(RuntimeError, "cannot schedule new futures after shutdown"),
        )
        submit_more_done[0] = True

    futures = [executor.submit(submit_more) for _ in (1, 2, 3)]

    # Let threads proceed only after shutdown has already started...
    def set_soon():
        time.sleep(0.10)
        proceed.set()

    proceed_f = Executors.thread_pool(max_workers=1).submit(set_soon)
    executor.shutdown(wait=True)
    proceed_f.result()

    # It should have reached here without deadlocking

    # All futures should have completed
    assert all([f.done() for f in futures])

    # And the tests in submit_more should have run
    assert_that(submit_more_done[0], equal_to(True))
