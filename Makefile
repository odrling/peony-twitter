.PHONY: test doc clean test_deps

help:
	@echo "Please use \`make <target>\` where <target> is one of"
	@echo "  install    to install the dependencies required to run the tests"
	@echo "  test       to test peony"
	@echo "  doc        to make the documentation (html)"
	@echo "  clean      to clean the repository"

clean:
	@rm -rf build dist .cache .coverage* .tox
	@rm -rf *.egg-info
	@python3 setup.py clean --all > /dev/null 2> /dev/null

doc:
	sphinx-build -b html -d build/doctrees docs build/html
	@printf "\nBuild finished. The HTML pages are in build/html.\n"

install:
	pip3 install --upgrade pip wheel
	pip3 install --upgrade -r tests_requirements.txt

test:
	py.test --cov=peony --cov-report term-missing -v tests
