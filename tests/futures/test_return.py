from more_executors import f_return, f_return_error


def test_f_return():
    value = "quux"
    assert f_return(value).result() is value


def test_f_return_no_value():
    assert f_return().result() is None


def test_f_return_error():
    exception = RuntimeError("simulated error")
    assert f_return_error(exception).exception() is exception
