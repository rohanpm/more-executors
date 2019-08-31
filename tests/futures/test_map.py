from more_executors.futures import f_map, f_return


def div10(x):
    return 10 / x


def test_map_nothing():
    map_in = f_return(10)
    mapped = f_map(map_in)
    assert mapped.result() == 10


def test_map():
    map_in = f_return(10)
    mapped = f_map(map_in, div10)
    assert mapped.result() == 1


def test_map_error():
    map_in = f_return(0)

    # This one should fail...
    mapped = f_map(map_in, div10)

    # Now map it through an error handler
    mapped = f_map(mapped, error_fn=str)

    result = mapped.result()
    assert "division" in result
