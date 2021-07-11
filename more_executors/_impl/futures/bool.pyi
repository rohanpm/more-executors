from typing import Any, TypeVar
from concurrent.futures import Future

A = TypeVar("A")
B = TypeVar("B")

def f_or(f: Future[A], *fs: Future[B]) -> Future[A | B]: ...
def f_and(f: Future[A], *fs: Future[B]) -> Future[A | B]: ...
