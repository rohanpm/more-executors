import traceback

from more_executors.futures import f_sequence, f_traverse, f_return, f_return_error

from ..util import get_traceback


def div100by_async(x):
    return f_return(100.0 / x)


def test_sequence():
    f = f_sequence([
        f_return('a'),
        f_return('b'),
        f_return('c')
    ])
    assert f.result() == ['a', 'b', 'c']


def test_sequence_error():
    error = ValueError('simulated error')
    f = f_sequence([
        f_return('a'),
        f_return_error(error),
        f_return('c')
    ])
    assert f.exception() is error


def test_traverse():
    future = f_traverse(div100by_async, [10, 25, 50])
    assert future.result() == [10, 4, 2]


def test_traverse_generator():
    future = f_traverse(div100by_async, range(10, 26, 5))
    assert future.result() == [10, 100/15., 5, 4]


def test_traverse_error():
    future = f_traverse(div100by_async, [10, 0, 50])
    exception = future.exception()

    assert isinstance(exception, ZeroDivisionError)

    assert 'div100by_async' in ''.join(traceback.format_tb(get_traceback(future)))
