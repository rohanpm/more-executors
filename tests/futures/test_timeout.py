import time

from concurrent.futures import CancelledError
from more_executors import Executors
from more_executors.futures import f_timeout, f_nocancel


def test_timeout():
    def sleep_then_return(x):
        time.sleep(x)
        return x

    with Executors.thread_pool(max_workers=2) as executor:
        futures = [
            executor.submit(sleep_then_return, x) for x in [0.5, 0.5, 0.5, 0.5, 0.5]
        ]
        futures[3] = f_nocancel(futures[3])
        futures = [f_timeout(f, 0.02) for f in futures]

        try:
            futures[-1].result()
            raise AssertionError("Should have failed")
        except CancelledError:
            # expected
            pass

        assert futures[0].result() == 0.5
        assert futures[1].result() == 0.5
        assert futures[2].cancelled()
        assert futures[3].result() == 0.5
        assert futures[4].cancelled()
