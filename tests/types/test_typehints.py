import sys
import os
import glob

import pytest


THIS_DIR = os.path.dirname(__file__)
EXAMPLES = os.path.join(THIS_DIR, "type-examples")

ALL_FILES = [os.path.basename(path) for path in glob.glob(EXAMPLES + "/*")]


@pytest.mark.parametrize("file", ALL_FILES)
def test_typehint(file):
    if sys.version_info < (3, 9, 0):
        pytest.skip("need python 3.9")

    path = os.path.join(EXAMPLES, file)

    import mypy.api

    (out, err, code) = mypy.api.run(
        ["--disallow-any-expr", "--follow-imports", "skip", path]
    )

    print(out)
    print(err)
    assert code == 0
