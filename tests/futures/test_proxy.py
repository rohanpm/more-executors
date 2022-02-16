from math import floor, ceil, trunc
from threading import Semaphore
import pytest


from more_executors import Executors
from more_executors.futures import f_return, f_return_error, f_proxy, f_map


def test_len():
    xlist = f_proxy(f_return([1, 2, 3]))
    xint = f_proxy(f_return(42))
    xstr = f_proxy(f_return("hello"))

    assert len(xlist) == 3
    assert len(xstr) == 5

    with pytest.raises(TypeError) as exc:
        len(xint)
    assert "has no len" in str(exc.value)


def test_attrs():
    xdict = f_proxy(f_return({"foo": "bar", "baz": "quux"}))

    assert sorted(xdict.keys()) == ["baz", "foo"]
    assert sorted(xdict.values()) == ["bar", "quux"]

    with pytest.raises(AttributeError):
        xdict.no_such_attr()


def test_dict():
    xdict = f_proxy(f_return({"foo": "bar", "baz": "quux"}))

    assert xdict["foo"] == "bar"
    assert "baz" in xdict

    xdict["added"] = 123
    assert "added" in xdict

    del xdict["foo"]
    assert "foo" not in xdict

    with pytest.raises(KeyError):
        assert xdict["no_such_key"]


def test_iter():
    xlist = f_proxy(f_return(["a", "b", "c"]))
    xstr = f_proxy(f_return("xyz"))
    xint = f_proxy(f_return(12))

    list_elems = []
    for elem in xlist:
        list_elems.append(elem)
    assert list_elems == ["a", "b", "c"]

    str_elems = []
    for elem in xstr:
        str_elems.append(elem)
    assert str_elems == ["x", "y", "z"]

    with pytest.raises(TypeError) as exc:
        for _ in xint:
            pass
    assert "not iterable" in str(exc.value)


def test_math_basic():
    xstr = f_proxy(f_return("xyz"))
    xint = f_proxy(f_return(12))
    xfloat = f_proxy(f_return(5.0))

    assert xstr * 2 == "xyzxyz"
    assert xstr + "abc" == "xyzabc"

    assert xint + 2 == 14
    assert xint - 2 == 10
    assert xint % 10 == 2
    assert xint / 2 == 6
    assert xint ** 2 == 144

    assert xfloat // 2.0 == 2.0

    assert divmod(xint, 5) == (2, 2)


def test_math_round():
    xstr = f_proxy(f_return("xyz"))
    xint = f_proxy(f_return(12))
    xfloat = f_proxy(f_return(5.5))

    assert round(xint) == 12
    assert round(xfloat) == 6.0

    assert floor(xint) == 12
    assert floor(xfloat) == 5.0

    assert ceil(xint) == 12
    assert ceil(xfloat) == 6.0

    assert trunc(xint) == 12
    assert trunc(xfloat) == 5.0

    with pytest.raises(Exception):
        assert round(xstr) == "foo"


def test_bits():
    xbin = f_proxy(f_return(0b00110))

    assert xbin << 1 == 0b01100
    assert xbin >> 1 == 0b00011
    assert xbin & 0b10010 == 0b00010
    assert xbin | 0b10010 == 0b10110
    assert xbin ^ 0b10010 == 0b10100


def test_sign():
    xint = f_proxy(f_return(123))
    xnegint = f_proxy(f_return(-123))

    assert -xint == -123
    assert +xint == 123
    assert abs(xnegint) == 123
    assert ~xint == -124
    assert ~xnegint == 122
    assert ~~xint == 123
    assert ~~xnegint == -123


def test_num_types():
    xint = f_proxy(f_return(123))
    xfloat = f_proxy(f_return(1.23))

    assert float(xint) == 123.0
    assert complex(xint) == complex(123)
    assert int(xfloat) == 1


def test_bool():
    xtrue = f_proxy(f_return(True))
    xfalse = f_proxy(f_return(False))
    xempty = f_proxy(f_return([]))

    # All of these count as truthy, as we want to allow testing if
    # a future was returned without blocking
    assert xtrue
    assert xfalse
    assert xempty


def test_map():
    sem = Semaphore(0)
    with Executors.thread_pool() as exc:
        # This future cannot possibly proceed until we unblock the semaphore.
        f = exc.submit(sem.acquire)
        f = f_proxy(f)

        # If bug #278 exists, we will hang here indefinitely.
        f = f_map(f, lambda _: 123)

        # If bug is fixed, future is still not evaluated.
        # Let it proceed now.
        sem.release()
        assert f.result() == 123


def test_attribute_error():
    error = AttributeError("quux!")
    prox = f_proxy(f_return_error(error))

    # I should be able to get the exception normally
    assert prox.exception() is error

    # If I try to iterate, it should raise the exception
    with pytest.raises(Exception) as excinfo:
        iter(prox)

    # The raised exception should be exactly the underlying value
    assert excinfo.value is error
