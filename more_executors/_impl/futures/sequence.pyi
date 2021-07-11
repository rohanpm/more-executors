from concurrent.futures import Future
from typing import TypeVar
from collections.abc import Iterable, Callable

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")

def f_sequence(futures: Iterable[Future[T]]) -> Future[list[T]]: ...
def f_traverse(fn: Callable[[A], Future[B]], xs: Iterable[A]) -> Future[list[B]]: ...
