from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from hamcrest import assert_that, instance_of

from more_executors import Executors
from more_executors.retry import RetryExecutor
from more_executors.map import MapExecutor


def test_thread_pool():
    assert_that(Executors.thread_pool(), instance_of(ThreadPoolExecutor))


def test_process_pool():
    assert_that(Executors.process_pool(), instance_of(ProcessPoolExecutor))


def test_retry():
    assert_that(Executors.thread_pool().with_retry(), instance_of(RetryExecutor))


def test_map():
    assert_that(Executors.thread_pool().with_map(lambda x: 10/x), instance_of(MapExecutor))
