from concurrent.futures import Future
from typing import TypeVar, overload

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")

@overload
def f_zip() -> Future[tuple]: ...
@overload
def f_zip(f1: Future[A]) -> Future[tuple[A]]: ...
@overload
def f_zip(f1: Future[A], f2: Future[B]) -> Future[tuple[A, B]]: ...
@overload
def f_zip(f1: Future[A], f2: Future[B], f3: Future[C]) -> Future[tuple[A, B, C]]: ...

# TODO: is there any way to make this work perfectly for arbitrary number of futures?
@overload
def f_zip(
    f1: Future, f2: Future, f3: Future, f4: Future, *fs: Future
) -> Future[tuple]: ...
