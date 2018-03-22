from concurrent.futures import TimeoutError
from hamcrest import assert_that, equal_to, is_, calling, raises
from pytest import fixture
import time

from more_executors._executors import Executors


@fixture
def executor():
    return Executors.thread_pool().with_timeout(0.01)


def test_basic_timeout(executor):
    def fn(sleep_time, retval):
        time.sleep(sleep_time)
        return retval

    f1 = executor.submit(fn, 1.0, 'abc')
    f2 = executor.submit(fn, 1.0, 'def')

    # Default should time out
    assert_that(calling(f1.result), raises(TimeoutError))
    assert_that(calling(f2.exception), raises(TimeoutError))

    # But specifying a value should make it work
    assert_that(f1.result(2.0), equal_to('abc'))
    assert_that(f1.exception(), is_(None))

    assert_that(f2.exception(2.0), is_(None))
    assert_that(f2.result(), equal_to('def'))
