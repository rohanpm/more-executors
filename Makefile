default: help


help:
	@echo Try one of the following:
	@echo
	@echo "   make check - run all autotests"
	@echo "   make cov   - run tests and open coverage report"

check:
	@tox

cov:
	@tox -e cov
	@xdg-open htmlcov/index.html
