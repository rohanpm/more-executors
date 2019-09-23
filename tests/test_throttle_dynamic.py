from threading import Semaphore
import time
import pytest

from more_executors import Executors

from .util import assert_soon


class ThrottleTester(object):
    def __init__(self):
        self.sem = Semaphore(0)

        self.entered = []
        self.exited = []

    @property
    def running_count(self):
        return len(self.exited) - len(self.entered)

    def proceed(self):
        self.sem.release()

    def proceed_all(self):
        for _ in range(0, self.running_count):
            self.sem.release()

    def __call__(self):
        self.entered.append(None)
        self.sem.acquire()
        self.exited.append(None)


def test_throttle_dynamic():
    throttle = [0]

    executor = Executors.thread_pool(max_workers=8).with_throttle(
        count=lambda: throttle[0]
    )

    tester = ThrottleTester()

    futures = []

    for _ in range(0, 50):
        futures.append(executor.submit(tester))

    # Currently, it should not be possible for any to execute
    time.sleep(0.5)

    assert not tester.entered
    assert tester.running_count == 0

    # If we raise the throttle...
    throttle[0] = 1

    # Then one should be able to start
    assert_soon(lambda: tester.running_count == 1)

    # If we raise it again...
    throttle[0] = 2

    # Let the first one complete so it wakes faster
    tester.proceed()

    # Now two should be able to start
    assert_soon(lambda: tester.running_count == 2)

    # If we unset throttle entirely...
    throttle[0] = None

    # Then all threads should be used
    assert_soon(lambda: tester.running_count == 8)

    # Throttle back to zero
    throttle[0] = 0

    # Let them all finish
    tester.proceed_all()

    # There should NOT be any more able to run
    assert tester.running_count == 0
    time.sleep(0.5)
    assert tester.running_count == 0

    # Raise throttle again works fine
    throttle[0] = 6
    assert_soon(lambda: tester.running_count == 6)

    # Let them all finish
    for _ in range(0, 100):
        tester.proceed()

    assert_soon(lambda: len(tester.exited) == 50)


def test_throttle_dynamic_raises_cannot_construct():
    """Can't make a ThrottleExecutor if count immediately raises"""

    error = RuntimeError("oops")

    def raise_error():
        raise error

    with pytest.raises(RuntimeError) as exc_info:
        Executors.sync().with_throttle(count=raise_error)
    assert exc_info.value is error


def test_throttle_dynamic_raises_uses_previous(caplog):
    """ThrottleExecutor uses last throttle value if the callable raises"""
    called = []

    def throttle_count():
        if called:
            raise RuntimeError("oops")
        called.append(None)
        return 1

    tester = ThrottleTester()
    executor = Executors.thread_pool(max_workers=2).with_throttle(count=throttle_count)

    f1 = executor.submit(tester)
    f2 = executor.submit(tester)
    f3 = executor.submit(tester)

    # There should be one running
    assert_soon(lambda: tester.running_count == 1)

    tester.proceed()

    # First future should be able to complete
    f1.result(10.0)

    # There should still one running
    assert_soon(lambda: tester.running_count == 1)

    tester.proceed()
    tester.proceed()

    # They can all complete
    f2.result(10.0)
    f3.result(10.0)

    if caplog:
        # It should have logged a warning about the error
        message = "\n".join(caplog.messages)
        assert "Error evaluating throttle count" in message
