.PHONY: help clean doc install format test release

all: .formatted test

help:
	@echo "Please use \`make <target>\` where <target> is one of"
	@echo "  clean      to clean the repository"
	@echo "  doc        to make the documentation (html)"
	@echo "  format     to correct code style"
	@echo "  test       to test peony"

clean:
	@rm -rf build dist .cache .coverage* .tox
	@rm -rf *.egg-info
	@rm -f .installed
	@rm -f .formatted
	@rm -f .format_test
	@rm -rf tests/cache
	@python3 setup.py clean --all > /dev/null 2> /dev/null

doc: build/html

build/html: docs
	sphinx-build -b html -d build/doctrees docs build/html
	@printf "\nBuild finished. The HTML pages are in build/html.\n"

install: .installed

.installed: dev_requirements.txt tests_requirements.txt requirements.txt
	pip3 install --upgrade pip wheel
	pip3 install --upgrade -r dev_requirements.txt
	@touch .installed

format: .formatted

.formatted: .installed peony examples tests
	isort -rc examples peony tests > /dev/null
	autopep8 -r --in-place examples peony tests
	autoflake -r --in-place examples peony tests
	@touch .formatted

.format_test: .installed peony examples tests
	flake8
	@touch .format_test

test: .installed .format_test
	py.test --cov=peony --cov-report term-missing --durations=20 tests

release:
	python3 setup.py sdist bdist_wheel
	twine upload dist/*
