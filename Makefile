.PHONY: help clean doc format install test release

all: test

help:
	@echo "Please use \`make <target>\` where <target> is one of"
	@echo "  clean      to clean the repository"
	@echo "  doc        to make the documentation (html)"
	@echo "  format     to check code style"
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

build/html: $(wildcard docs/*) $(wildcard docs/*/*)
	sphinx-build -b html -d build/doctrees docs build/html
	@printf "\nBuild finished. The HTML pages are in build/html.\n"

install: .installed

.installed: dev_requirements.txt tests_requirements.txt requirements.txt
	pip3 install --upgrade pip wheel
	pip3 install --upgrade -r dev_requirements.txt
	@touch .installed

PYFILES = $(shell find * -type f -name "*.py" | grep -v '__init__.py')

.formatted: $(PYFILES)
	flake8 $?
	@touch .formatted

format: install .formatted

test: install format
	py.test --cov=peony --cov-report term-missing --durations=20 tests
