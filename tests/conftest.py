import sys

import pytest


if sys.version_info < (2, 7, 0):

    @pytest.fixture
    def caplog():
        # On Python 2.6, any tests depending on caplog fixture are effectively
        # skipped as it is not present on the available pytest versions.
        yield None
