from typing import TypeVar
import logging

from .shared_types import ExecutorProtocol

T = TypeVar("T")

class SyncExecutor(ExecutorProtocol):
    def __init__(
        self, logger: logging.Logger | None = ..., name: str = ...
    ) -> None: ...
    def __enter__(self) -> SyncExecutor: ...
