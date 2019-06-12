import time
from more_executors import Executors
from more_executors.futures import f_nocancel


def delay_then(x, delay=0.01):
    time.sleep(delay)
    return x


def test_nocancel():
    executor = Executors.thread_pool(max_workers=2)

    futures = [f_nocancel(executor.submit(delay_then, x)) for x in [1, 2, 3, 4, 5]]

    for f in futures:
        # Should not be able to cancel it even though most
        # are not started yet
        assert not f.cancel()

    assert [f.result() for f in futures] == [1, 2, 3, 4, 5]
