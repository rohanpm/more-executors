from concurrent.futures import Future

from more_executors.futures import f_zip, f_return, f_return_error


def test_zip_none():
    future = f_zip()
    assert future.result() == ()


def test_zip_single():
    value = "foobar"
    future = f_zip(f_return(value))
    assert future.result() == (value,)


def test_zip_two():
    future = f_zip(f_return("a"), f_return("b"))
    assert future.result() == ("a", "b")


def test_zip_three():
    f_a = f_return("a")
    f_b = f_return("b")
    f_c = f_return("c")
    future = f_zip(f_a, f_b, f_c)
    assert future.result() == ("a", "b", "c")


def test_zip_error():
    error = RuntimeError("simulated error")
    f_a = f_return("a")
    f_b = f_return_error(error)
    f_c = f_return("c")
    future = f_zip(f_a, f_b, f_c)
    assert future.exception() is error


def test_zip_cancel():
    f_a = f_return("a")
    f_b = Future()
    f_c = Future()
    future = f_zip(f_a, f_b, f_c)

    future.cancel()

    assert f_b.cancelled()
    assert f_c.cancelled()


def test_zip_large():
    fs = [f_return(i) for i in range(0, 100000)]
    future = f_zip(*fs)
    result = future.result()
    assert result[0:5] == (0, 1, 2, 3, 4)
    assert len(result) == 100000
