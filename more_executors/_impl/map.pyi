from typing import Any, Generic, TypeVar
from collections.abc import Callable

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

A = TypeVar("A")
B = TypeVar("B")

class MapExecutor(TypedExecutorProtocol[A, B]):
    def __init__(
        self,
        delegate: ExecutorProtocol,
        fn: Callable[[A], B] = ...,
        logger: Any | None = ...,
        name: str = ...,
        **kwargs
    ) -> None: ...
    def __enter__(self) -> MapExecutor[A, B]: ...
