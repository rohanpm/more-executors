default: help

.PHONY:

help:
	@echo Try one of the following:
	@echo
	@echo "   make check   - run all autotests"
	@echo "   make cov     - run tests and open coverage report"
	@echo "   make debug   - run tests with configuration appropriate for debugging"
	@echo "   make docs    - build documentation"
	@echo "   make release - upload a release to PyPI"

check:
	@tox

cov:
	@tox -e cov
	@xdg-open htmlcov/index.html

debug:
	env PYTHONPATH=$$PWD py.test -v --log-cli-level=DEBUG -o log_cli=true

docs: .PHONY
	@tox -e docs

release: .PHONY
	tox -e py35
	.tox/py35/bin/pip install pypandoc
	env USE_PANDOC=1 .tox/py35/bin/python scripts/release
