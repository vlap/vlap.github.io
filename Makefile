# Load environment variables from .env
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Configuration
REPO_ROOT := $(shell pwd)
PYTHON    := /home/volant/miniconda2/bin/python3
HUGO      := hugo

.PHONY: help sync build serve deploy watch

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  sync    Mirror data and sync PDFs from Dropbox"
	@echo "  build   Sync and build the Hugo site"
	@echo "  serve   Run Hugo local development server"
	@echo "  deploy  Build and push changes to GitHub"
	@echo "  watch   Automatically sync/deploy when Dropbox changes (requires inotify-tools)"

sync:
	@echo "==> Fetching ORCID data..."
	@$(PYTHON) scripts/fetch_orcid.py
	@echo "==> Fetching Google Scholar stats..."
	@$(PYTHON) scripts/fetch_scholar.py
	@echo "==> Fetching GitHub activity..."
	@$(PYTHON) scripts/fetch_github.py
	@echo "==> Mirroring YAML data and conversion..."
	@$(PYTHON) scripts/bib_to_yaml.py
	@# Direct mirror of YAML files from Dropbox to Repo data/
	@rsync -avz --include="*.yaml" --exclude="*" "$(DROPBOX_CV_PATH)/" data/
	@echo "==> Updating site statistics..."
	@$(PYTHON) scripts/update_stats.py
	@echo "==> Syncing PDF downloads..."
	@mkdir -p static/downloads
	@rsync -avz --include="*.pdf" --exclude="*" "$(DROPBOX_CV_PATH)/" static/downloads/
	@if [ -d "$(DROPBOX_IMAGE_PATH)" ]; then \
		echo "==> Syncing images..."; \
		mkdir -p static/images/research; \
		rsync -avz --include="*.jpg" --include="*.png" --include="*.svg" --include="*.gif" --exclude="*" "$(DROPBOX_IMAGE_PATH)/" static/images/research/; \
	fi

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

watch:
	@echo "==> Watching for changes in Dropbox CV path..."
	@while true; do \
		inotifywait -r -e modify,create,delete "$(DROPBOX_CV_PATH)"; \
		make deploy; \
	done
