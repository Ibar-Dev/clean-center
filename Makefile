SHELL := /bin/bash
COMPOSE ?= docker compose
UV ?= uv
SANITY_ARGS ?=

.DEFAULT_GOAL := help

.PHONY: help sanity-check sanity-check-up sanity-check-verbose

help:
	@echo "Objetivos disponibles:"
	@echo "  make sanity-check           Verifica un stack ya levantado"
	@echo "  make sanity-check-up        Levanta/recompila el stack y verifica"
	@echo "  make sanity-check-verbose   Verifica con detalle adicional"
	@echo ""
	@echo "Argumentos extra:"
	@echo "  make sanity-check SANITY_ARGS='--product-id 3 --quantity 2'"

sanity-check:
	$(UV) run python scripts/sanity_check.py $(SANITY_ARGS)

sanity-check-up:
	$(COMPOSE) up -d --build --wait --wait-timeout 180
	$(UV) run python scripts/sanity_check.py $(SANITY_ARGS)

sanity-check-verbose:
	$(UV) run python scripts/sanity_check.py --verbose $(SANITY_ARGS)
