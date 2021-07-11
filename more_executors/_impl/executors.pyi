from .asyncio import AsyncioExecutor as AsyncioExecutor
from .bind import BoundCallable as BoundCallable
from .cancel_on_shutdown import CancelOnShutdownExecutor as CancelOnShutdownExecutor
from .flat_map import FlatMapExecutor as FlatMapExecutor
from .map import MapExecutor as MapExecutor
from .poll import PollExecutor as PollExecutor
from .retry import RetryExecutor as RetryExecutor
from .sync import SyncExecutor as SyncExecutor
from .throttle import ThrottleExecutor as ThrottleExecutor
from .timeout import TimeoutExecutor as TimeoutExecutor
from .wrapped import (
    CustomizableProcessPoolExecutor as CustomizableProcessPoolExecutor,
    CustomizableThreadPoolExecutor as CustomizableThreadPoolExecutor,
)

from .shared_types import ExecutorProtocol

class Executors:
    @classmethod
    def bind(cls, executor, fn): ...
    @classmethod
    def flat_bind(cls, executor, fn): ...
    @classmethod
    def thread_pool(cls, *args, **kwargs) -> ExecutorProtocol: ...
    @classmethod
    def process_pool(cls, *args, **kwargs): ...
    @classmethod
    def sync(cls, *args, **kwargs) -> SyncExecutor: ...
    @classmethod
    def with_retry(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_map(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_flat_map(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_poll(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_timeout(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_throttle(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_cancel_on_shutdown(cls, executor, *args, **kwargs): ...
    @classmethod
    def with_asyncio(cls, executor, *args, **kwargs): ...
