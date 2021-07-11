from concurrent.futures import Future
from typing import Any, TypeVar
import logging
from collections.abc import Callable

from .shared_types import ExecutorProtocol, TypedExecutorProtocol

A = TypeVar("A")
B = TypeVar("B")
T = TypeVar("T")

class RetryPolicy(object): ...

class ExceptionRetryPolicy(RetryPolicy):
    def __init__(self, **kwargs): ...

class RetryExecutor(ExecutorProtocol):
    def __init__(
        self,
        delegate,
        retry_policy: Any | None = ...,
        logger: logging.Logger | None = ...,
        name: str = ...,
        **kwargs
    ): ...
    def submit_retry(
        self, retry_policy: RetryPolicy, fn: Callable[..., T], *args, **kwargs
    ) -> Future[T]: ...
    def __enter__(self) -> RetryExecutor: ...

class TypedRetryExecutor(TypedExecutorProtocol[A, B]):
    def submit_retry(
        self, retry_policy: RetryPolicy, fn: Callable[..., A], *args, **kwargs
    ) -> Future[B]: ...
    def __enter__(self) -> TypedRetryExecutor[A, B]: ...
