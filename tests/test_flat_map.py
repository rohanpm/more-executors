from pytest import fixture
from hamcrest import assert_that, equal_to, instance_of, calling, raises

from more_executors import Executors
from more_executors.flat_map import FlatMapExecutor


@fixture
def executor():
    return Executors.thread_pool()


def add1(x):
    return x + 1


def mult10(x):
    return x * 10


def div10by(x):
    return 10 / x


def test_basic_flat_map(executor):
    flat_map_executor = FlatMapExecutor(executor, lambda x: executor.submit(mult10, x))

    inputs = [1, 2, 3]
    expected_result = [20, 40, 60]

    futures = [flat_map_executor.submit(lambda x: x * 2, x) for x in inputs]
    results = [f.result() for f in futures]

    assert_that(results, equal_to(expected_result))


def test_flat_map_exception(executor):
    flat_map_executor = FlatMapExecutor(executor, lambda x: executor.submit(div10by, x))

    inputs = [1, 2, 0]

    futures = [flat_map_executor.submit(lambda v: v, x) for x in inputs]

    # First two should succeed and give the mapped value
    assert_that(futures[0].result(), equal_to(10))
    assert_that(futures[1].result(), equal_to(5))

    # The third should have crashed
    assert_that(futures[2].exception(), instance_of(ZeroDivisionError))
    assert_that(calling(futures[2].result), raises(ZeroDivisionError))


def test_flat_map_nofuture(executor):
    """Executor raises TypeError if map function does not produce a Future."""

    flat_map_executor = FlatMapExecutor(
        executor, lambda x: executor.submit(mult10, x) if x == 2 else mult10(x)
    )

    inputs = [1, 2, 3]

    futures = [flat_map_executor.submit(lambda v: v, x) for x in inputs]

    # The second future should have returned the mapped value
    assert_that(futures[1].result(), equal_to(20))

    # The others should have failed since returned value is not a Future
    assert_that(futures[0].exception(), instance_of(TypeError))
    assert_that(calling(futures[2].result), raises(TypeError))


def test_chained_flat_map(executor):
    """Chaining multiple flatmaps pass through values as expected."""

    flat_map_executor = executor.with_flat_map(
        lambda x: executor.submit(mult10, x)
    ).with_flat_map(lambda x: executor.submit(add1, x))

    inputs = [1, 2]

    futures = [flat_map_executor.submit(lambda v: v, x) for x in inputs]

    # It should have produced the expected values
    assert_that(futures[0].result(), equal_to(11))
    assert_that(futures[1].result(), equal_to(21))


def test_chained_flat_map_exception(executor):
    """Executor propagates innermost exception in the case of chained flatmaps."""

    my_exception = RuntimeError("testing")
    fn2_called = []

    def fn1(x):
        raise my_exception

    def fn2(x):
        fn2_called.append(0)
        raise AssertionError("Can't get here!")  # pragma: no cover

    flat_map_executor = executor.with_flat_map(fn1).with_flat_map(fn2)

    inputs = [1, 2]

    futures = [flat_map_executor.submit(lambda v: v, x) for x in inputs]

    # The innermost exception should have been raised (exactly)
    assert_that(futures[0].exception() is my_exception)
    assert_that(futures[1].exception() is my_exception)

    # The outermost function should never have been called
    assert_that(fn2_called, equal_to([]))
