from concurrent.futures import Future
from typing import TypeVar

T = TypeVar("T")

# TODO: is there any way we can express that the returned value
# will share most of the properties of T?
def f_proxy(f: Future[T], **kwargs) -> Future[T]: ...
