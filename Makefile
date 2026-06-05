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

build:
	make -C $(FORGE_DIR) build

deploy:
	make -C $(FORGE_DIR) deploy

start:
	make -C $(FORGE_DIR) forge start

stop:
	make -C $(FORGE_DIR) forge stop
