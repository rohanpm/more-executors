"""Helper to get shutdown-aware instances of Event.

Call get_event to get instances of threading.Event.

These events work like any other event except that they will be automatically
set() during interpreter exit.  If an event has been set() for this reason,
is_shutdown() will return True.
"""

from threading import Event, RLock
import weakref
import atexit


class ShutdownAwareEventHandler(object):
    def __init__(self):
        self.lock = RLock()
        self.atexit_registered = False
        self.shutdown = False
        # NOTE: no weakset until python <2.7 is dropped
        self.events = []

    def clean_events(self, *_args, **_kwargs):
        with self.lock:
            self.events = [evt_ref for evt_ref in self.events if evt_ref()]

    def on_exiting(self):
        self.shutdown = True

        for evt_ref in self.events:
            evt = evt_ref()
            if evt:
                evt.set()

    def get_event(self):
        with self.lock:
            if not self.atexit_registered:
                atexit.register(self.on_exiting)
                self.atexit_registered = True
            out = Event()
            self.events.append(weakref.ref(out, self.clean_events))
            return out


GLOBAL_HANDLER = ShutdownAwareEventHandler()
get_event = GLOBAL_HANDLER.get_event


def is_shutdown():
    return GLOBAL_HANDLER.shutdown
