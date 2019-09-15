from more_executors import Executors
from more_executors.retry import RetryPolicy


def test_broken_policy(caplog):
    """Executor logs without retry if policy raises exception"""

    policy_error = RuntimeError("error from policy")
    fn_error = RuntimeError("error from fn")

    class BrokenRetryPolicy(RetryPolicy):
        def should_retry(self, attempt, future):
            raise policy_error

    executor = Executors.thread_pool().with_retry(retry_policy=BrokenRetryPolicy())

    def fn():
        raise fn_error

    # Start the callable
    future = executor.submit(fn)

    # It should fail with the error raised from the fn
    assert future.exception(10.0) is fn_error

    if not caplog:
        # TODO: remove me when py2.6 support is dropped
        return

    records = caplog.records
    error_log = records[-1]

    # It should have logged a message about the error
    assert "Exception while evaluating retry policy" in error_log.message
    assert "BrokenRetryPolicy" in error_log.message
    assert "error from policy" in error_log.exc_text
