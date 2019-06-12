import pytest


from more_executors.futures import (
    f_or,
    f_and,
    f_map,
    f_flat_map,
    f_zip,
    f_apply,
    f_nocancel,
    f_timeout,
)


def test_or_error():
    with pytest.raises(TypeError):
        f_or("a", "b")


def test_and_error():
    with pytest.raises(TypeError):
        f_and("a", "b")


def test_map_error():
    with pytest.raises(TypeError):
        f_map("a", lambda x: x)

    with pytest.raises(TypeError):
        f_map(future="a", fn=lambda x: x)


def test_flat_map_error():
    with pytest.raises(TypeError):
        f_flat_map("a", lambda x: x)

    with pytest.raises(TypeError):
        f_flat_map(future="a", fn=lambda x: x)


def test_zip_error():
    with pytest.raises(TypeError):
        f_zip("a", "b", "c")


def test_apply_error():
    with pytest.raises(TypeError):
        f_apply("a", "b", "c")


def test_nocancel():
    with pytest.raises(TypeError):
        f_nocancel("a")

    with pytest.raises(TypeError):
        f_nocancel(future="a")


def test_timeout():
    with pytest.raises(TypeError):
        f_timeout("a", 123.0)
