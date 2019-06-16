from more_executors._impl.helpers import executor_loop


def test_raises_typical():
    exc = RuntimeError("simulated error")

    def my_fn():
        raise exc

    wrapped_fn = executor_loop(my_fn)

    try:
        wrapped_fn()
        raise AssertionError("Was expected to raise!")
    except Exception as actual:
        assert actual is exc


def test_catches_shutdown():
    # sic...
    exc = RuntimeError("cannot schedule new futures afterinterpreter shutdown")

    def my_fn():
        raise exc

    wrapped_fn = executor_loop(my_fn)

    # It should not raise
    wrapped_fn()
