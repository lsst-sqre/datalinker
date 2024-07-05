.PHONY: help
help:
	@echo "Make targets for datalinker"
	@echo "make init - Set up dev environment"
	@echo "make run - Run development instance of server"
	@echo "make update - Update pinned dependencies and run make init"
	@echo "make update-deps - Update pinned dependencies"
	@echo "make update-deps-no-hashes - Pin dependencies without hashes"

.PHONY: init
init:
	pip install --upgrade pip uv
	uv pip install -r requirements/main.txt -r requirements/dev.txt \
	    -r requirements/tox.txt
	uv pip install --editable .
	rm -rf .tox
	uv pip install --upgrade pre-commit
	pre-commit install

.PHONY: update
update: update-deps init

.PHONY: update-deps
update-deps:
	pip install --upgrade pip uv
	uv pip install --upgrade pre-commit
	pre-commit autoupdate
	uv pip compile --upgrade --generate-hashes			\
	    --output-file requirements/main.txt requirements/main.in
	uv pip compile --upgrade --generate-hashes			\
	    --output-file requirements/dev.txt requirements/dev.in
	uv pip compile --upgrade --generate-hashes			\
	    --output-file requirements/tox.txt requirements/tox.in

# Useful for testing against a Git version of a dependency.
.PHONY: update-deps-no-hashes
update-deps-no-hashes:
	pip install --upgrade uv
	uv pip compile --upgrade					\
	    --output-file requirements/main.txt requirements/main.in
	uv pip compile --upgrade					\
	    --output-file requirements/dev.txt requirements/dev.in
	uv pip compile --upgrade					\
	    --output-file requirements/tox.txt requirements/tox.in

.PHONY: run
run:
	tox -e run
