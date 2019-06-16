import logging
from functools import wraps

LOG = logging.getLogger(__name__)


def executor_loop(fn):
    @wraps(fn)
    def out(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RuntimeError as error:
            if "cannot schedule new futures after" in str(error):
                LOG.debug("Ignoring error due to interpreter shutdown", exc_info=1)
                return
            raise

    return out
