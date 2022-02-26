from functools import partial
from more_executors import Executors, SyncExecutor


def mult2(x):
    return 2 * x


def mult10(x):
    return 10 * x


def mult(x, y):
    return x * y


class mult_class(object):
    def __init__(self, operand):
        self.operand = operand

    def __call__(self, x):
        return x * self.operand


def async_mult(x, y):
    return SyncExecutor().submit(mult, x, y)


def test_single_bind():
    async_mult2 = Executors.thread_pool().bind(mult2)

    inputs = [0, 1, 2]
    futures = [async_mult2(x) for x in inputs]
    results = [f.result() for f in futures]

    assert results == [0, 2, 4]


def test_bind_with_partial():
    async_mult2 = Executors.thread_pool().bind(partial(mult, 2))

    inputs = [0, 1, 2]
    futures = [async_mult2(x) for x in inputs]
    results = [f.result() for f in futures]

    assert results == [0, 2, 4]


def test_bind_with_callable():
    async_mult2 = Executors.thread_pool().bind(mult_class(2))

    inputs = [0, 1, 2]
    futures = [async_mult2(x) for x in inputs]
    results = [f.result() for f in futures]

    assert results == [0, 2, 4]


def test_bind_then_map():
    async_mult200 = (
        Executors.thread_pool().with_map(mult10).bind(mult2).with_map(mult10)
    )

    inputs = [0, 1, 2]
    futures = [async_mult200(x) for x in inputs]
    results = [f.result() for f in futures]

    assert results == [0, 200, 400]


def test_flat_bind():
    bound_async_mult = Executors.thread_pool().flat_bind(async_mult)

    inputs = [(0, 1), (2, 3), (4, 5)]
    expected_results = [0, 6, 20]
    futures = [bound_async_mult(x, y) for (x, y) in inputs]
    results = [f.result() for f in futures]

    assert results == expected_results


def test_no_rebind():
    bound = Executors.sync().bind(mult10)

    try:
        bound.bind(mult2)
        raise AssertionError("Chained bind should have failed!")  # pragma: no cover
    except AttributeError:
        pass
