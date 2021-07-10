from functools import partial

import prometheus_client  # pylint: disable=import-error


Counter = partial(prometheus_client.Counter, namespace="more_executors")
Gauge = partial(prometheus_client.Gauge, namespace="more_executors")


class PrometheusMetrics(object):
    TIMEOUT = Counter(
        "timeout", "Futures cancelled due to timeout", labelnames=("executor",)
    )
    SHUTDOWN_CANCEL = Counter(
        "shutdown_cancel", "Futures cancelled at shutdown", labelnames=("executor",)
    )
    EXEC_INPROGRESS = Gauge(
        "exec_inprogress", "Executors currently in use", labelnames=("type", "executor")
    )
    EXEC_TOTAL = Counter(
        "exec_total", "Total executors used", labelnames=("type", "executor")
    )
    FUTURE_INPROGRESS = Gauge(
        "future_inprogress", "Futures currently in use", labelnames=("type", "executor")
    )
    FUTURE_TOTAL = Counter(
        "future_total", "Total futures used", labelnames=("type", "executor")
    )
    FUTURE_CANCEL = Counter(
        "future_cancel", "Futures cancelled", labelnames=("type", "executor")
    )
    FUTURE_ERROR = Counter(
        "future_error", "Futures resolved with error", labelnames=("type", "executor")
    )
    FUTURE_TIME = Counter(
        "future_time",
        "Total execution time of futures",
        labelnames=("type", "executor"),
    )
    POLL_TOTAL = Counter(
        "poll_total", "PollExecutor's poll function calls", labelnames=("executor",)
    )
    POLL_ERROR = Counter(
        "poll_error",
        "PollExecutor's poll function calls raising an error",
        labelnames=("executor",),
    )
    POLL_TIME = Counter(
        "poll_time",
        "Total execution time of PollExecutor's poll function",
        labelnames=("executor",),
    )
    RETRY_TOTAL = Counter(
        "retry_total", "Futures retried by RetryExecutor", labelnames=("executor",)
    )
    RETRY_QUEUE = Gauge(
        "retry_queue", "Futures in RetryExecutor queue", labelnames=("executor",)
    )
    RETRY_DELAY = Counter(
        "retry_delay", "Time spent waiting for retry", labelnames=("executor",)
    )
    # TODO: figure out how to implement this one
    # THROTTLE_TOTAL = Counter("throttle_total", "Futures throttled by ThrottleExecutor")
    THROTTLE_QUEUE = Gauge(
        "throttle_queue", "Futures in ThrottleExecutor queue", labelnames=("executor",)
    )
