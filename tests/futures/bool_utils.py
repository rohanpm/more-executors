import pytest

from more_executors.futures import f_return, f_return_error, f_return_cancelled


CANCELLED = object()


FALSEY = {
    'False': False,
    'None': None,
    'emptystr': '',
    'emptylist': [],
    'emptydict': {},
    'zero': 0,
    'error': RuntimeError('simulated error'),
    'cancelled': CANCELLED,
}

TRUTHY = {
    'True': True,
    'object': object(),
    'num': 123,
    'str': 'testing',
    'list': ['foo'],
    'dict': {'key': 'val'},
}


@pytest.fixture(params=FALSEY.keys())
def falsey(request):
    return FALSEY[request.param]


@pytest.fixture(params=TRUTHY.keys())
def truthy(request):
    return TRUTHY[request.param]


def as_future(x):
    if x is CANCELLED:
        return f_return_cancelled()
    elif isinstance(x, Exception):
        return f_return_error(x)
    return f_return(x)


def assert_future_equal(future, value):
    if value is CANCELLED:
        assert future.cancelled()
    elif isinstance(value, Exception):
        assert future.exception() == value
    else:
        assert future.result() == value


def resolve_value(value, falsey_instance, truthy_instance):
    if value is falsey:
        return falsey_instance
    if value is truthy:
        return truthy_instance
    return value


def resolve_inputs(values, falsey_real, truthy_real):
    return [resolve_value(x, falsey_real, truthy_real) for x in values]
