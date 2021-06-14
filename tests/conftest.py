import sys
import os

import pytest


if sys.version_info < (2, 7, 0):

    @pytest.fixture
    def caplog():
        # On Python 2.6, any tests depending on caplog fixture are effectively
        # skipped as it is not present on the available pytest versions.
        yield None


@pytest.fixture(autouse=True)
def set_debug_var():
    os.environ["MORE_EXECUTORS_DEBUG"] = "1"
    yield
    del os.environ["MORE_EXECUTORS_DEBUG"]
