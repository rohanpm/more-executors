from concurrent.futures import Executor
from typing import Any, Generic, TypeVar
from collections.abc import Callable
import logging

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

A = TypeVar("A")
B = TypeVar("B")

class PollDescriptor(Generic[A, B]):
    @property
    def result(self) -> A: ...
    def yield_result(self, result: B) -> None: ...
    def yield_exception(
        self, exception: BaseException, traceback: Any | None = ...
    ) -> None: ...

class PollExecutor(TypedExecutorProtocol[A, B]):
    def __init__(
        self,
        delegate: ExecutorProtocol,
        poll_fn: Callable[[list[PollDescriptor[A, B]]], int | float | None],
        cancel_fn: Callable[[A], bool] | None = ...,
        default_interval: float = ...,
        logger: logging.Logger | None = ...,
        name: str = ...,
    ): ...
    def notify(self) -> None: ...
    def __enter__(self) -> PollExecutor[A, B]: ...
