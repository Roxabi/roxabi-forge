FORGE_DIR   := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
SCRIPTS_DIR := $(FORGE_DIR)scripts

-include $(FORGE_DIR).env
export CLOUDFLARE_ACCOUNT_ID
export CLOUDFLARE_API_TOKEN

.PHONY: build deploy du serve help

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build   regenerate manifest + sync to _dist/"
	@echo "  deploy  build then deploy to Cloudflare Pages"
	@echo "  du      disk usage by project"
	@echo "  serve   local gallery on :8080 (foreground, Ctrl+C)"

build:
	@bash "$(SCRIPTS_DIR)/build.sh"

deploy: build
	@cd "$(FORGE_DIR)" && { git rev-parse --is-inside-work-tree >/dev/null 2>&1 && ! git diff --quiet 2>/dev/null; } && { echo "Error: dirty tree — commit changes before deploying"; exit 1; } || true
	@echo "Deploying to Cloudflare Pages..."
	@npx wrangler pages deploy "$(FORGE_DIR)_dist" --project-name=forge --branch=main

du:
	@du -sh "$(FORGE_DIR)"*/

serve:
	@test -f "$(FORGE_DIR)serve.py" && test -f "$(FORGE_DIR)run.sh" || { \
		echo "Error: forge not initialized at $(FORGE_DIR)"; \
		echo "       Run plugin deploy first: make -C ~/projects/roxabi-forge/plugins/forge deploy"; \
		exit 1; \
	}
	@exec "$(FORGE_DIR)run.sh"