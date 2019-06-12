from __future__ import print_function

import logging
import collections
import pprint
from threading import Lock

from monotonic import monotonic


class CollectionLogger(logging.Logger, object):
    """This logger appends log messages onto a collection.

    Implemented as a logger rather than a handler because it's the simplest
    way to integrate with monotonic() - built-in loggers do not support
    setting "created" on log records by a custom clock."""

    def __init__(self, collection):
        self.collection = collection
        self.lock = Lock()
        super(CollectionLogger, self).__init__(collection)

    def callHandlers(self, record):
        now = monotonic()
        record_msg = record.msg % record.args
        msg = "%s: %s" % (now, record_msg)
        with self.lock:
            self.collection.append(msg)


def add_debug_logging(ex):
    """Hack the logger on an executor (if any) so that it records messages
    with timestamps on the executor itself.

    This is intended to integrate with the dump_executor function, so that
    events on an executor can be easily seen after a test failure.

    Note that it hijacks the usual logging, so e.g. pytest's log capturing
    won't work any more."""
    delegate = getattr(ex, "_delegate", None)
    if delegate:
        add_debug_logging(delegate)

    if not getattr(ex, "_log", None):
        return

    logs = collections.deque(maxlen=1000)
    logger = CollectionLogger(logs)
    logger.setLevel(logging.DEBUG)

    ex.__logs = logs
    ex._log = logger


def dump_executor(ex):
    print("Executor %s:" % ex)

    all_vars = vars(ex)
    # Don't worry about the with_* stuff from Executors
    dump_vars = {}
    for key, val in all_vars.items():
        if key.startswith("with_"):
            continue
        dump_vars[key] = val

    if "__logs" in dump_vars:
        lock = dump_vars["_log"].lock
    else:
        lock = Lock()

    with lock:
        pprint.pprint(dump_vars, indent=2, width=400)

    delegate = getattr(ex, "_delegate", None)
    if delegate:
        print("")
        dump_executor(delegate)
