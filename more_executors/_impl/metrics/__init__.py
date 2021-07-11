import logging
from functools import partial

from monotonic import monotonic

from .null import NullMetrics

LOG = logging.getLogger("more-executors.metrics")

try:  # pylint: disable=import-error
    from .prometheus import PrometheusMetrics

    metrics = PrometheusMetrics()
except Exception:
    LOG.debug("disabling prometheus support", exc_info=True)

    metrics = NullMetrics()  # type: ignore


def record_done(f, started_when, time, inprogress, cancelled, failed):
    inprogress.dec()

    run_time = monotonic() - started_when
    time.inc(run_time)

    if f.cancelled():
        cancelled.inc()
    elif f.exception():
        failed.inc()


def track_future(f, **labels):
    if "executor" not in labels:
        # TODO: when using the future composition functions like
        # f_or, f_map etc, we'll often get here. But it might be possible
        # to do something better? e.g. if we have one future chained from
        # another, can we copy the label from the other?
        labels["executor"] = "default"

    metrics.FUTURE_TOTAL.labels(**labels).inc()

    start = monotonic()

    inprogress = metrics.FUTURE_INPROGRESS.labels(**labels)
    inprogress.inc()

    time = metrics.FUTURE_TIME.labels(**labels)

    cancelled = metrics.FUTURE_CANCEL.labels(**labels)
    failed = metrics.FUTURE_ERROR.labels(**labels)
    cb = partial(
        record_done,
        started_when=start,
        time=time,
        inprogress=inprogress,
        cancelled=cancelled,
        failed=failed,
    )

    f.add_done_callback(cb)

    return f
