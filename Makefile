.PHONY: help
help:
	@echo "Make targets for datalinker"
	@echo "make init - Set up dev environment"
	@echo "make run - Run development instance of server"
	@echo "make update - Update pinned dependencies and run make init"
	@echo "make update-deps - Update pinned dependencies"

.PHONY: init
init:
	pip install --upgrade pip uv
	uv pip install -r requirements/main.txt -r requirements/dev.txt \
	    -r requirements/tox.txt
	uv pip install --editable .
	rm -rf .tox
	uv pip install --upgrade pre-commit
	pre-commit install

.PHONY: run
run:
	tox -e run

.PHONY: update
update: update-deps init

.PHONY: update-deps
update-deps:
	pip install --upgrade pip uv
	uv pip install --upgrade pre-commit
	pre-commit autoupdate
	uv pip compile --upgrade --universal --generate-hashes		\
	    --output-file requirements/main.txt pyproject.toml
	uv pip compile --upgrade --universal --generate-hashes		\
	    --output-file requirements/dev.txt requirements/dev.in
	uv pip compile --upgrade --universal --generate-hashes		\
	    --output-file requirements/tox.txt requirements/tox.in
