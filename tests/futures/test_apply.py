from more_executors.futures import f_return, f_apply


def mult2(x):
    return x * 2


def mult(x, y, *rest):
    out = x * y
    for val in rest:
        out = out * val
    return out


def dump_args(*args, **kwargs):
    return (args, kwargs)


def test_f_apply_no_arg():
    applied = f_apply(f_return(lambda: 42))
    assert applied.result() == 42


def test_f_apply_single_arg():
    applied = f_apply(f_return(mult2), f_return(42))
    assert applied.result() == 84


def test_f_apply_multi_arg():
    applied = f_apply(f_return(mult), f_return(3), f_return(4), f_return(2))
    assert applied.result() == 24


def test_f_apply_kwargs():
    applied = f_apply(f_return(dump_args), key1=f_return(42), key2=f_return(12))
    assert applied.result() == ((), {"key1": 42, "key2": 12})


def test_f_apply_mixed():
    applied = f_apply(
        f_return(dump_args),
        f_return("a"),
        f_return("b"),
        f_return("c"),
        key1=f_return("val1"),
        key2=f_return("val2"),
        key3=f_return("val3"),
    )
    assert applied.result() == (
        ("a", "b", "c"),
        {"key1": "val1", "key2": "val2", "key3": "val3"},
    )
