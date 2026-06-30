SHELL := /bin/bash -o pipefail

FORGE_DIR          := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
SCRIPTS_DIR        := $(FORGE_DIR)scripts
SYSTEMD_USER_DIR   ?= $(HOME)/.config/systemd/user
FORGE_UNIT         := forge

ifndef SVC_CMD
ifeq (forge,$(firstword $(MAKECMDGOALS)))
  SVC_CMD := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq (,$(SVC_CMD))
    $(eval $(SVC_CMD):;@:)
  endif
endif
endif

-include $(FORGE_DIR).env
export CLOUDFLARE_ACCOUNT_ID
export CLOUDFLARE_API_TOKEN

.PHONY: build deploy du forge install-service help

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build            regenerate manifest + sync to _dist/"
	@echo "  deploy           build then deploy to Cloudflare Pages"
	@echo "  du               disk usage by project"
	@echo "  install-service  install forge systemd user unit"
	@echo "  forge <action>   start|stop|reload|status|logs|errlogs"

build:
	@bash "$(SCRIPTS_DIR)/build.sh"

deploy: build
	@cd "$(FORGE_DIR)" && { git rev-parse --is-inside-work-tree >/dev/null 2>&1 && ! git diff --quiet 2>/dev/null; } && { echo "Error: dirty tree — commit changes before deploying"; exit 1; } || true
	@echo "Deploying to Cloudflare Pages..."
	@npx wrangler pages deploy "$(FORGE_DIR)_dist" --project-name=forge --branch=main

du:
	@du -sh "$(FORGE_DIR)"*/

install-service:
	@mkdir -p "$(SYSTEMD_USER_DIR)" "$(HOME)/.local/state/forge/logs"
	@test -f "$(FORGE_DIR)forge.service" || { echo "Error: $(FORGE_DIR)forge.service missing — run plugin deploy first."; exit 1; }
	@install -m 644 "$(FORGE_DIR)forge.service" "$(SYSTEMD_USER_DIR)/$(FORGE_UNIT).service"
	@systemctl --user daemon-reload
	@echo "Installed $(SYSTEMD_USER_DIR)/$(FORGE_UNIT).service"
	@echo "Start with: systemctl --user start $(FORGE_UNIT)"

forge:
	@case "$(SVC_CMD)" in \
		start|reload|restart|"") \
			if [ ! -f "$(FORGE_DIR)serve.py" ] || [ ! -f "$(FORGE_DIR)run.sh" ]; then \
				echo "Error: forge not initialized at $(FORGE_DIR)"; \
				echo "       Run plugin deploy first."; \
				exit 1; \
			fi ;; \
	esac
	@case "$(SVC_CMD)" in \
		start|"")       systemctl --user start $(FORGE_UNIT) ;; \
		stop)           systemctl --user stop $(FORGE_UNIT) ;; \
		reload|restart) systemctl --user restart $(FORGE_UNIT) ;; \
		status)         systemctl --user status $(FORGE_UNIT) || true ;; \
		logs)           journalctl --user -u $(FORGE_UNIT) -f ;; \
		errlogs|errors) journalctl --user -u $(FORGE_UNIT) -f -p err ;; \
		*) echo "Unknown action: $(SVC_CMD). Use: start|stop|reload|status|logs|errlogs"; exit 1 ;; \
	esac