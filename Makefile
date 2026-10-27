.PHONY: help env up down restart logs ps migrate knowledge reload test shell bash

help:
	@echo "make env       create env/.env from the example, if it is missing"
	@echo "make up        build and start the stack"
	@echo "make down      stop and remove containers"
	@echo "make restart   restart the stack"
	@echo "make logs      follow web logs"
	@echo "make ps        show service status"
	@echo "make migrate   apply database migrations"
	@echo "make knowledge rebuild the knowledge base from documents/ and refresh the dump"
	@echo "make reload    replace the knowledge base with the dump from the repo"
	@echo "make test      run the offline test suite in a container"
	@echo "make shell     open a Django shell in the web container"
	@echo "make bash      open a shell in the web container"

env:
	@test -f env/.env || cp env/.env.example env/.env
	@echo "Using env/.env"

up: env
	docker compose up --build

down:
	docker compose down

restart: env
	docker compose restart

logs:
	docker compose logs -f web

ps:
	docker compose ps

migrate:
	docker compose exec web python manage.py migrate

knowledge: env
	docker compose run --rm \
		-v "$(CURDIR)/documents:/app/documents:ro" \
		-v "$(CURDIR)/fixtures:/app/fixtures" \
		web sh -c "python manage.py seed_event && python manage.py dump_knowledge"

reload:
	docker compose exec web python manage.py load_knowledge --force

test: env
	docker compose run --rm --build --no-deps --entrypoint "" web python -m pytest

shell:
	docker compose exec web python manage.py shell

bash:
	docker compose exec web sh
