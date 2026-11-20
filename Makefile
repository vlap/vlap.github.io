# Load environment variables from .env
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Configuration
REPO_ROOT := $(shell pwd)
PYTHON := python3
HUGO := hugo
CV_DIR ?= ../cv

.PHONY: help sync build build-site serve deploy fetch-web-stats test test-browser scan verify

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  sync             Sync sanitized CV data and PDFs from $(CV_DIR)"
	@echo "  fetch-web-stats  Fetch external metrics from OpenAlex and update stats"
	@echo "  build            Sync and build the Hugo site"
	@echo "  build-site       Build the Hugo site without syncing $(CV_DIR)"
	@echo "  test             Run Python static build, DOM, CSS, and script tests"
	@echo "  test-browser     Run headless Chromium E2E, accessibility, and CWV tests"
	@echo "  scan             Run modern-web-guidance legacy-scan for first-party code"
	@echo "  verify           Run build-site, test, test-browser, and scan"
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
	@$(HUGO) --gc --minify --cleanDestinationDir

build-site:
	@echo "==> Building site..."
	@$(HUGO) --gc --minify --cleanDestinationDir

test:
	@echo "==> Running pytest suite..."
	@$(PYTHON) -m pytest -q

test-browser:
	@echo "==> Running headless Chromium verification..."
	@node --test tests/browser_verify.mjs

scan:
	@echo "==> Running modern-web-guidance legacy-scan..."
	@$(PYTHON) scripts/check_modern_web.py

verify: build-site test test-browser scan

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
