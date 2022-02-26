"""A library of composable Python executors.

- [Documentation](https://rohanpm.github.io/more-executors/)
- [Source](https://github.com/rohanpm/more-executors)
- [PyPI](https://pypi.python.org/pypi/more-executors)

This library is intended for use with the
[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
module.  It includes a collection of `Executor` implementations in order to
extend the behavior of `Future` objects.

Compatible with Python 2.6, 2.7 and 3.x.

This documentation was built from an unknown revision.
"""
from ._impl.executors import Executors
from . import futures
from . import asyncio
from . import cancel_on_shutdown
from . import flat_map
from . import map  # pylint: disable=redefined-builtin
from . import poll
from . import retry
from . import sync
from . import throttle
from . import timeout

from .futures import *
from .asyncio import *
from .cancel_on_shutdown import *
from .flat_map import *
from .map import *
from .poll import *
from .retry import *
from .sync import *
from .throttle import *
from .timeout import *

__all__ = ["Executors", "futures"]
__all__.extend(futures.__all__)
__all__.extend(asyncio.__all__)
__all__.extend(cancel_on_shutdown.__all__)
__all__.extend(flat_map.__all__)
__all__.extend(map.__all__)
__all__.extend(poll.__all__)
__all__.extend(retry.__all__)
__all__.extend(sync.__all__)
__all__.extend(throttle.__all__)
__all__.extend(timeout.__all__)
