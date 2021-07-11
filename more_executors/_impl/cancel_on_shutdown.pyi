import logging
from typing import TypeVar

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

A = TypeVar("A")
B = TypeVar("B")

class CancelOnShutdownExecutor(ExecutorProtocol):
    def __init__(
        self,
        delegate: ExecutorProtocol,
        logger: logging.Logger | None = ...,
        name: str = ...,
    ) -> None: ...
    def __enter__(self) -> CancelOnShutdownExecutor: ...

class TypedCancelOnShutdownExecutor(TypedExecutorProtocol[A, B]):
    def __enter__(self) -> TypedCancelOnShutdownExecutor[A, B]: ...
