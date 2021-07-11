from typing import TypeVar
from concurrent.futures import Future

T = TypeVar("T")

def f_timeout(future: Future[T], timeout: float | int) -> Future[T]: ...
