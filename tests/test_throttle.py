import pytest

from threading import Lock
import time

from hamcrest import assert_that, less_than_or_equal_to, equal_to, instance_of

from more_executors import Executors, ThrottleExecutor


@pytest.mark.parametrize("block", [True, False])
def test_throttle(block):
    THREADS = 8
    COUNT = 3
    samples = []
    running_now = []
    lock = Lock()

    def record(x):
        with lock:
            running_now.append(x)

        samples.append(running_now[:])

        # Need to ensure the function takes some time to run
        # so the futures don't complete as fast as we submit them
        time.sleep(0.001)

        with lock:
            running_now.remove(x)

    futures = []
    executor = ThrottleExecutor(
        Executors.thread_pool(max_workers=THREADS), count=COUNT, block=block
    )
    with executor:
        for i in range(0, 1000):
            future = executor.submit(record, i)
            futures.append(future)

        # They should all be able to complete
        for future in futures:
            future.result(30.0)

    # Now have a look at running counts
    max_len = 0
    for i, sample in enumerate(samples):
        # There should never have been more futures running than the limit
        sample_len = len(sample)
        assert_that(sample_len, less_than_or_equal_to(COUNT), "failed at step %s" % i)
        max_len = max(max_len, sample_len)

    # It should have been able to run up to the limit too
    assert_that(max_len, equal_to(COUNT))


def test_with_throttle():
    assert_that(
        Executors.sync(name="throttle-test").with_throttle(4, block=True),
        instance_of(ThrottleExecutor),
    )
