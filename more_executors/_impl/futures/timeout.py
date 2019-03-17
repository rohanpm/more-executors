# -*- coding: utf-8 -*-

import weakref
from threading import Lock

from more_executors import Executors


LOCK = Lock()
EXECUTOR_REF = None


def f_timeout(future, timeout):
    """Wrap a future to cancel it after a timeout is reached.

    Signature: :code:`Future<X>, float ⟶ Future<X>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.
        timeout (float)
            A timeout to apply to the future, in seconds.

    Returns:
        :class:`~concurrent.futures.Future`
            A wrapped version of :obj:`future` which may be cancelled if the
            future has not completed within :obj:`timeout` seconds.

            Note: only a single attempt is made to cancel the future, and there
            is no guarantee that the cancel will succeed.

    .. versionadded:: 1.19.0
    """
    return timeout_executor().submit_timeout(timeout, lambda: future)


def timeout_executor():
    global EXECUTOR_REF  # pylint: disable=global-statement
    with LOCK:
        executor = EXECUTOR_REF and EXECUTOR_REF()
        if not executor:
            executor = Executors.sync().with_flat_map(lambda x: x).with_timeout(None)
            EXECUTOR_REF = weakref.ref(executor)
        return executor
