import time


def assert_soon(fn):
    for _ in range(0, 1000):
        try:
            fn()
            break
        except AssertionError:
            time.sleep(0.01)
    else:
        fn()
