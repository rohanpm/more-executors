from typing import Any, TypeVar
from collections.abc import Callable
from concurrent.futures import Future

T = TypeVar("T")

def f_apply(
    future_fn: Future[Callable[..., T]], *future_args: Future, **future_kwargs: Future
) -> Future[T]: ...
