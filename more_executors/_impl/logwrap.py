import os


class LogWrapper(object):
    # A helper to veto all debug logs unless MORE_EXECUTORS_DEBUG is set.
    #
    # The point here is that, even for DEBUG level, we can be a bit too verbose.
    def __init__(self, logger):
        self._delegate = logger
        self._debug = os.environ.get("MORE_EXECUTORS_DEBUG", "0") == "1"
        self.info = logger.info
        self.exception = logger.exception

    def debug(self, *args, **kwargs):
        if self._debug:
            return self._delegate.debug(*args, **kwargs)
