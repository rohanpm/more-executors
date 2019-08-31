from more_executors.futures import f_flat_map, f_return, f_return_error


def div10(x):
    try:
        return f_return(10 / x)
    except Exception as ex:
        return f_return_error(ex)


def raise_str(x):
    raise RuntimeError("oops, an error: %s" % x)


def test_flat_map_nothing():
    map_in = f_return(10)
    mapped = f_flat_map(map_in)
    assert mapped.result() == 10


def test_flat_map():
    map_in = f_return(10)
    mapped = f_flat_map(map_in, div10)
    assert mapped.result() == 1


def test_flat_map_error():
    map_in = f_return(0)

    # This one should fail...
    mapped = f_flat_map(map_in, div10)

    # Now map it through an error handler
    mapped = f_flat_map(mapped, error_fn=lambda ex: f_return(str(ex)))

    result = mapped.result()
    assert "division" in result


def test_flat_map_error_fn_raises():
    map_in = f_return(0)

    # This one should fail...
    mapped = f_flat_map(map_in, div10)

    # Now map it through an error handler
    mapped = f_flat_map(mapped, error_fn=raise_str)

    ex = mapped.exception()
    assert "division" in str(ex)
    assert "oops, an error" in str(ex)
