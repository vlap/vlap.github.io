# Load environment variables from .env
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Configuration
REPO_ROOT := $(shell pwd)
PYTHON    := python3
HUGO      := hugo
CV_DIR    ?= ../cv

.PHONY: help sync build serve deploy fetch-web-stats

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  sync             Sync sanitized CV data and PDFs from $(CV_DIR)"
	@echo "  fetch-web-stats  Fetch external metrics from OpenAlex and update stats"
	@echo "  build            Sync and build the Hugo site"
	@echo "  serve            Run Hugo local development server"
	@echo "  deploy           Build and push changes to GitHub"

fetch-web-stats:
	@echo "==> Fetching OpenAlex metrics..."
	@$(PYTHON) scripts/fetch_openalex.py
	@echo "==> Updating site statistics..."
	@$(PYTHON) scripts/update_stats.py

sync:
	@echo "==> Exporting CV bundle from $(CV_DIR)..."
	@/home/volant/code/career/cv/tex/venv/bin/python $(CV_DIR)/tex/scripts/export_site_bundle.py --site-dir .
	@echo "==> Updating site statistics..."
	@$(PYTHON) scripts/update_stats.py

build: sync
	@echo "==> Building site..."
	@$(HUGO) --gc --minify

serve:
	@$(HUGO) server -D

deploy: build
	@echo "==> Checking for changes..."
	@if [ -n "$$(git status -s)" ]; then \
		echo "==> Committing and pushing..."; \
		git add .; \
		git commit -m "chore: automated sync $$(date +'%Y-%m-%d %H:%M')"; \
		git push origin main; \
	else \
		echo "==> No changes to deploy."; \
	fi
