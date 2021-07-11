from typing import TypeVar, Any
import logging
from collections.abc import Callable
from concurrent.futures import Future

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")

class TimeoutExecutor(ExecutorProtocol):
    def __init__(
        self,
        delegate: ExecutorProtocol | TypedExecutorProtocol[object, object],
        timeout: float | int,
        logger: logging.Logger | None = ...,
        name: str = ...,
    ): ...
    def submit_timeout(
        self, timeout: float | int, fn: Callable[..., T], *args, **kwargs
    ) -> Future[T]: ...
    def __enter__(self) -> TimeoutExecutor: ...

class TypedTimeoutExecutor(TypedExecutorProtocol[A, B]):
    def submit_timeout(
        self, timeout: float | int, fn: Callable[..., A], *args, **kwargs
    ) -> Future[B]: ...
    def __enter__(self) -> TypedTimeoutExecutor[A, B]: ...
