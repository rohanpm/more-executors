from typing import TypeVar
from .map import MapExecutor

A = TypeVar("A")
B = TypeVar("B")

class FlatMapExecutor(MapExecutor[A, B]):
    def __enter__(self) -> FlatMapExecutor[A, B]: ...
