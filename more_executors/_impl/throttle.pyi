from typing import TypeVar, Any
import logging
from collections.abc import Callable
from concurrent.futures import Future

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

A = TypeVar("A")
B = TypeVar("B")

class ThrottleExecutor(ExecutorProtocol):
    def __init__(
        self,
        delegate: ExecutorProtocol,
        count: int | Callable[[], int],
        logger: logging.Logger | None = ...,
        name: str = ...,
    ): ...
    def __enter__(self) -> ThrottleExecutor: ...

class TypedThrottleExecutor(TypedExecutorProtocol[A, B]):
    def __init__(
        self,
        delegate: ExecutorProtocol,
        count: int | Callable[[], int],
        logger: logging.Logger | None = ...,
        name: str = ...,
    ): ...
    def __enter__(self) -> TypedThrottleExecutor[A, B]: ...
