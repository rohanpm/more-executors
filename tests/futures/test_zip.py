from more_executors.futures import f_zip, f_return


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
