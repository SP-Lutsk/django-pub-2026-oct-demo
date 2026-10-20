.PHONY: help env up down restart logs ps migrate seed test shell bash

help:
	@echo "make env       create env/.env from the example, if it is missing"
	@echo "make up        build and start the stack"
	@echo "make down      stop and remove containers"
	@echo "make restart   restart the stack"
	@echo "make logs      follow web logs"
	@echo "make ps        show service status"
	@echo "make migrate   apply database migrations"
	@echo "make seed      reindex event materials"
	@echo "make test      run the offline test suite"
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

seed:
	docker compose exec web python manage.py seed_event

test:
	python -m pytest

shell:
	docker compose exec web python manage.py shell

bash:
	docker compose exec web sh
