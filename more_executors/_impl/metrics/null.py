class NullBase(object):
    def labels(self, **_kwargs):
        return self

    def inc(self, _value=1):
        pass


class Counter(NullBase):
    pass


class Gauge(NullBase):
    def dec(self, _value=1):
        pass


class NullMetrics(object):
    TIMEOUT = Counter()
    SHUTDOWN_CANCEL = Counter()
    EXEC_INPROGRESS = Gauge()
    EXEC_TOTAL = Counter()
    FUTURE_INPROGRESS = Gauge()
    FUTURE_TOTAL = Counter()
    FUTURE_CANCEL = Counter()
    FUTURE_ERROR = Counter()
    FUTURE_TIME = Counter()
    POLL_TOTAL = Counter()
    POLL_ERROR = Counter()
    POLL_TIME = Counter()
    RETRY_TOTAL = Counter()
    RETRY_QUEUE = Gauge()
    RETRY_DELAY = Counter()
    THROTTLE_QUEUE = Gauge()
