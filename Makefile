export IMAGE_NAME := openclsim
export CONTAINER_NAME_APP := openclsim
export CONTAINER_NAME_DOCS := openclsim_docs

.PHONY: build up down test-up test docs log help check-local-env

## check-local-env : check if all needed commands/tools are available
check-local-env:
	@which docker &>/dev/null || (echo "[docker] not found, exit"; exit 1)
	@which docker-compose &>/dev/null || (echo "[docker-compose] not found, exit"; exit 1)
	@which git &>/dev/null || (echo "[git] not found, exit"; exit 1)
	@echo "Environment setup correctly"

## build : Build a new docker container from the current directory
build: check-local-env
	@docker build \
		-t $(IMAGE_NAME):latest \
		.
## up : Run application in dev mode (using docker-compose)
up:
	@docker-compose -f docker-compose.yml -f .devcontainer/docker-compose.yml up -d;

## down : Stop the application (using just 'docker-compose down' results in orphan containers/networks)
down:
	@docker-compose -f docker-compose.yml -f .devcontainer/docker-compose.yml down;

 ## test-up	: Run application in test mode (using docker-compose)
test-up:
	@docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d;

## test : Run the application tests (using docker-compose)
test: test-up
	@rm -f coverage.svg || true
	@docker exec $(CONTAINER_NAME_APP) bash -c "pip install -e .[testing]"
	@docker exec $(CONTAINER_NAME_APP) bash -c "pytest"
	@docker exec $(CONTAINER_NAME_APP) bash -c "pytest --nbmake ./notebooks --nbmake-kernel=python3 --ignore ./notebooks/.ipynb_checkpoints --ignore  ./notebooks/cleanup  --ignore ./notebooks/students   --verbose"
	@docker exec $(CONTAINER_NAME_APP) bash -c "rm -f coverage.svg; coverage-badge -o coverage.svg;"
	@docker cp $(CONTAINER_NAME_APP):/$(IMAGE_NAME)/coverage.svg .
	@docker-compose down

## docs : Generate docs
docs: test-up
	@docker exec $(CONTAINER_NAME_APP) bash -c "pip install -e .[docs]"
	# build from setup.py is no longer supported
	# https://github.com/sphinx-doc/sphinx/pull/11363
	@docker exec $(CONTAINER_NAME_APP) bash -c "sphinx-build docs docs/_build/html"
	@docker cp $(CONTAINER_NAME_APP):/$(IMAGE_NAME)/docs/_build/html/ html_docs
	@docker-compose down

## log : Start a log tail on the last docker-compose command
log:	
	@docker-compose logs -f --tail=100

## help : Show this help
help : Makefile
	@echo "Commands available in this makefile:"
	@sed -n 's/^##//p' $<
