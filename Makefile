.PHONY: help
help:
	@echo "Make targets for Gafaelfawr"
	@echo "make init - Set up dev environment"
	@echo "make run - Run development instance of server"
	@echo "make update - Update pinned dependencies and run make init"
	@echo "make update-deps - Update pinned dependencies"
	@echo "make update-deps-no-hashes - Pin dependencies without hashes"

.PHONY: init
init:
	pip install --upgrade pip
	pip install --upgrade pre-commit tox
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt
	rm -rf .tox
	pre-commit install

.PHONY: update
update: update-deps init

# The dependencies need --allow-unsafe because pre-commit transitively
# depends on setuptools, which is normally not allowed to appear in a hashed
# dependency file.
.PHONY: update-deps
update-deps:
	pip install --upgrade pre-commit
	pre-commit autoupdate
	pip install --upgrade pip-tools pip setuptools
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --allow-unsafe --generate-hashes				\
	    --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --allow-unsafe --generate-hashes				\
	    --output-file requirements/dev.txt requirements/dev.in

# Useful for testing against a Git version of a dependency.
.PHONY: update-deps-no-hashes
update-deps-no-hashes:
	pip install --upgrade pip-tools pip setuptools
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --allow-unsafe						\
	    --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --allow-unsafe						\
	    --output-file requirements/dev.txt requirements/dev.in

.PHONY: run
run:
	tox -e run
