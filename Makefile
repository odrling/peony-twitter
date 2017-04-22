.PHONY: test doc clean test_deps dev format

help:
	@echo "Please use \`make <target>\` where <target> is one of"
	@echo "  install    to install the dependencies required to run the tests"
	@echo "  test       to test peony"
	@echo "  doc        to make the documentation (html)"
	@echo "  clean      to clean the repository"
	@echo "  isort      to run isort on the project"

clean:
	@rm -rf build dist .cache .coverage* .tox
	@rm -rf *.egg-info
	@python3 setup.py clean --all > /dev/null 2> /dev/null

doc:
	sphinx-build -b html -d build/doctrees docs build/html
	@printf "\nBuild finished. The HTML pages are in build/html.\n"

install:
	pip3 install --upgrade pip wheel
	pip3 install --upgrade -r requirements.txt
	pip3 install --upgrade -r extras_require.txt


dev:
	pip3 install --upgrade pip wheel
	pip3 install --upgrade -r dev_requirements.txt

test:
	py.test --cov=peony --cov-report term-missing -v tests

format:
	@isort -rc peony > /dev/null
	@isort -rc tests > /dev/null
	@isort -rc examples > /dev/null
	@autopep8 -r --in-place peony
	@autopep8 -r --in-place examples
	@autopep8 -r --in-place tests
