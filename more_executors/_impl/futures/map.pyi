from concurrent.futures import Future
from typing import Any, Callable, TypeVar, overload

A = TypeVar("A")
B = TypeVar("B")

@overload
def f_map(
    future: Future[A],
) -> Future[A]: ...
@overload
def f_map(
    future: Future[A],
    fn: Callable[[A], B] | None = ...,
    error_fn: Callable[[Exception], B] | None = ...,
) -> Future[B]: ...
@overload
def f_flat_map(
    future: Future[A],
) -> Future[A]: ...
@overload
def f_flat_map(
    future: Future[A],
    fn: Callable[[A], Future[B]] | None = ...,
    error_fn: Callable[[Exception], Future[B]] | None = ...,
) -> Future[B]: ...
