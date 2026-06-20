FORGE_DIR       ?= $(HOME)/.roxabi/forge
PLUGIN_DIR      := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT       := $(abspath $(PLUGIN_DIR)../..)

SUPERVISOR_HUB  ?= $(HOME)/projects
-include $(SUPERVISOR_HUB)/hub.mk

.PHONY: deploy register help

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  deploy   copy server files, scripts, and runtime Makefile → $(FORGE_DIR)/"
	@echo "  register symlink supervisor config + generate hub delegation"
	@echo ""
	@echo "For day-to-day operations (build/deploy/start/stop/etc.):"
	@echo "  make -C $(FORGE_DIR) <target>"
	@echo "  or: make forge <target>  (from ~/projects/)"

deploy:
	@echo "── deploy forge → $(FORGE_DIR)/ ──"
	@mkdir -p "$(FORGE_DIR)/scripts"
	@cp -v $(PLUGIN_DIR)references/server/serve.py $(FORGE_DIR)/serve.py
	@cp -v $(PLUGIN_DIR)references/server/index.html $(FORGE_DIR)/index.html
	@cp -v $(PLUGIN_DIR)references/server/assets/favicon.svg $(FORGE_DIR)/favicon.svg
	@cp -v $(PLUGIN_DIR)references/server/assets/favicon-32.png $(FORGE_DIR)/favicon-32.png
	@cp -v $(PLUGIN_DIR)references/server/assets/apple-touch-icon.png $(FORGE_DIR)/apple-touch-icon.png
	@cp -v $(PLUGIN_DIR)references/server/assets/og-image.png $(FORGE_DIR)/og-image.png
	@cp -v $(PLUGIN_DIR)supervisor/scripts/run.sh $(FORGE_DIR)/run.sh
	@chmod +x $(FORGE_DIR)/run.sh
	@cp -v $(PLUGIN_DIR)runtime/Makefile $(FORGE_DIR)/Makefile
	@cp -v $(PLUGIN_DIR)runtime/.env.example $(FORGE_DIR)/.env.example
	@cp -v $(REPO_ROOT)/scripts/build.sh $(FORGE_DIR)/scripts/build.sh
	@cp -v $(REPO_ROOT)/scripts/gen-manifest.py $(FORGE_DIR)/scripts/gen-manifest.py
	@cp -v $(REPO_ROOT)/scripts/gen-deps.py $(FORGE_DIR)/scripts/gen-deps.py
	@cp -v $(REPO_ROOT)/scripts/gen-image-manifests.py $(FORGE_DIR)/scripts/gen-image-manifests.py
	@cp -v $(REPO_ROOT)/scripts/seed-meta.py $(FORGE_DIR)/scripts/seed-meta.py
	@cp -v $(REPO_ROOT)/scripts/update-meta.py $(FORGE_DIR)/scripts/update-meta.py
	@cp -v $(REPO_ROOT)/scripts/gen-og-tags.py $(FORGE_DIR)/scripts/gen-og-tags.py
	@cp -v $(REPO_ROOT)/scripts/gen-og-images.py $(FORGE_DIR)/scripts/gen-og-images.py
	@cp -v $(REPO_ROOT)/scripts/_og_common.py $(FORGE_DIR)/scripts/_og_common.py
	@cp -v $(REPO_ROOT)/scripts/render-md.py $(FORGE_DIR)/scripts/render-md.py
	@cp -v $(REPO_ROOT)/scripts/render-md-tabs.py $(FORGE_DIR)/scripts/render-md-tabs.py
	@chmod +x $(FORGE_DIR)/scripts/build.sh
	# gen-og-images.py / _og_common.py: invoked via 'uv run python3', no chmod +x needed
	@chmod +x $(FORGE_DIR)/scripts/render-md.py
	@chmod +x $(FORGE_DIR)/scripts/render-md-tabs.py
	@echo "── reference gallery + showcases ──"
	@cp -v $(PLUGIN_DIR)references/reference-gallery.html $(FORGE_DIR)/reference-gallery.html
	@mkdir -p "$(FORGE_DIR)/references/showcases" "$(FORGE_DIR)/references/graph-templates/examples"
	@cp -v $(PLUGIN_DIR)references/showcases/*.html "$(FORGE_DIR)/references/showcases/"
	@cp -v $(PLUGIN_DIR)references/graph-templates/examples/*.html "$(FORGE_DIR)/references/graph-templates/examples/"
	@echo "Done."
	@echo ""
	@echo "Note: if $(FORGE_DIR)/.env doesn't exist yet, copy .env.example and fill in credentials:"
	@echo "  cp $(FORGE_DIR)/.env.example $(FORGE_DIR)/.env"

register:
	@echo "Registering forge with supervisor hub..."
	@$(HUB_GEN_MK) forge "$(FORGE_DIR)" forge
	$(call hub-link-conf,forge,$(PLUGIN_DIR)supervisor/conf.d/forge.conf)
	$(hub_reread)
	@echo "Done."
