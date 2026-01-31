# Makefile for Django backend

.PHONY: help install dev migrate makemigrations test lint format deploy

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run development server"
	@echo "  make migrate      - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make format       - Format code with black"
	@echo "  make shell        - Open Django shell"
	@echo "  make superuser    - Create superuser"
	@echo "  make collectstatic - Collect static files"
	@echo "  make deploy       - Deploy to GAE"

install:
	pip install -r requirements.txt

dev:
	python manage.py runserver 0.0.0.0:3001

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

test:
	pytest --cov=. --cov-report=html

lint:
	flake8 .

format:
	black .

shell:
	python manage.py shell

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

deploy: collectstatic
	gcloud app deploy app.yaml --quiet
