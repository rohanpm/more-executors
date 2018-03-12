from concurrent.futures import ThreadPoolExecutor
from pytest import fixture
from hamcrest import assert_that, equal_to, instance_of, calling, raises

from more_executors.map import MapExecutor


@fixture
def executor():
    return ThreadPoolExecutor()


def test_basic_map(executor):
    map_executor = MapExecutor(executor, lambda x: x*10)

    inputs = [1, 2, 3]
    expected_result = [20, 40, 60]

    futures = [map_executor.submit(lambda x: x*2, x) for x in inputs]
    results = [f.result() for f in futures]

    assert_that(results, equal_to(expected_result))


def test_map_exception(executor):
    map_executor = MapExecutor(executor, lambda x: 10/x)

    inputs = [1, 2, 0]

    futures = [map_executor.submit(lambda v: v, x) for x in inputs]

    # First two should succeed and give the mapped value
    assert_that(futures[0].result(), equal_to(10))
    assert_that(futures[1].result(), equal_to(5))

    # The third should have crashed
    assert_that(futures[2].exception(), instance_of(ZeroDivisionError))
    assert_that(calling(futures[2].result), raises(ZeroDivisionError))
