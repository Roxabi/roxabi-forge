FORGE_DIR := $(HOME)/.roxabi/forge

.PHONY: build deploy start stop help

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build    regenerate manifest + sync to _dist/"
	@echo "  deploy   build then deploy to Cloudflare Pages"
	@echo "  start    start local dev server"
	@echo "  stop     stop local dev server"

define check_init
	@test -f $(FORGE_DIR)/Makefile || { echo "Error: forge not initialized — run: make -C plugins/forge deploy"; exit 1; }
endef

build:
	$(check_init)
	make -C $(FORGE_DIR) build

deploy:
	$(check_init)
	make -C $(FORGE_DIR) deploy

start:
	$(check_init)
	make -C $(FORGE_DIR) forge start

stop:
	$(check_init)
	make -C $(FORGE_DIR) forge stop
