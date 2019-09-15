import time
import gc
import traceback
import threading
from functools import partial


def assert_soon(fn):
    for _ in range(0, 1000):
        try:
            fn()
            break
        except AssertionError:
            time.sleep(0.01)
    else:
        fn()


def _run_or_record_exception(exception_list, retval_list, fn, *args, **kwargs):
    try:
        retval_list.append(fn(*args, **kwargs))
    except Exception as e:
        exception_list.append(e)


def run_or_timeout(fn, *args, **kwargs):
    timeout = kwargs.pop("timeout", 20.0)
    exception = []
    retval = []
    safe_fn = partial(_run_or_record_exception, exception, retval, fn)

    thread = threading.Thread(
        target=safe_fn, args=args, kwargs=kwargs, name="run_or_timeout"
    )
    thread.daemon = True
    thread.start()

    thread.join(timeout)

    if thread.is_alive():
        # Failed - did not complete within timeout
        raise AssertionError(
            "Function %s did not complete within %s seconds" % (fn, timeout)
        )

    if exception:
        # Failed - function raised
        raise exception[0]

    # OK!
    return retval[0]


def thread_names():
    return set([t.name for t in threading.enumerate()])


def assert_no_extra_threads(threads_before):
    gc.collect()
    threads_after = thread_names()
    extra_threads = threads_after - threads_before
    assert extra_threads == set()


def get_traceback(future):
    exception = future.exception()
    if "__traceback__" in dir(exception):
        return exception.__traceback__
    return future.exception_info()[1]


def assert_in_traceback(future, needle):
    tb = get_traceback(future)
    tb_str = "".join(traceback.format_tb(tb))
    assert needle in tb_str
