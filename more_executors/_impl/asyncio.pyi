from .metrics import metrics as metrics
from concurrent.futures import Executor
from typing import Any

class AsyncioExecutor(Executor):
    def __init__(
        self,
        delegate,
        loop: Any | None = ...,
        logger: Any | None = ...,
        name: str = ...,
    ) -> None: ...
    def submit(self, *args, **kwargs): ...
    def submit_with_loop(self, loop, fn, *args, **kwargs): ...
    def shutdown(self, wait: bool = ..., **_kwargs) -> None: ...
