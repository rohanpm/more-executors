from concurrent.futures import Future
from typing import TypeVar

T = TypeVar("T")

def f_nocancel(future: Future[T]) -> Future[T]: ...
