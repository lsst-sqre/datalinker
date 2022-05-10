.PHONY: update-deps
update-deps:
	pip install --upgrade pip-tools pip setuptools
	# Don't generate hashes here since we're installing daf_butler
	pip-compile --upgrade --build-isolation --allow-unsafe --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --build-isolation --allow-unsafe --output-file requirements/dev.txt requirements/dev.in

.PHONY: init
init:
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt
	rm -rf .tox
	pip install --upgrade tox
	pre-commit install

.PHONY: update
update: update-deps init

.PHONY: run
run:
	tox -e run
