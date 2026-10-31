# ==============================================================================
# Githeri Testbed & Autonomous Agent Worker Harness
# ==============================================================================
# Provides clean factory reset and scaffolding for agent test runs:
#   make clean-hermes
#   make clean-pi
#   make clean-opencode
#   make clean-claude
#   make clean-all
# ==============================================================================

SHELL := /bin/bash
VENV := .venv
PYTHON := $(shell if [ -f $(VENV)/bin/python ]; then echo "$(VENV)/bin/python"; else echo "python3"; fi)
GITHERI := $(shell if [ -f $(VENV)/bin/githeri ]; then echo "$(VENV)/bin/githeri"; else echo "githeri"; fi)

AGENTS := hermes pi opencode claude cursor deepseek chatgpt antigravity
CLEAN_TARGETS := $(addprefix clean-,$(AGENTS))
RESET_TARGETS := $(addprefix reset-,$(AGENTS))

.PHONY: help status update-githeri clean-all $(CLEAN_TARGETS) $(RESET_TARGETS)

help:
	@echo "╔══════════════════════════════════════════════════════════════════════════╗"
	@echo "║ Githeri Testbed — Autonomous Worker Factory Controller                  ║"
	@echo "╠══════════════════════════════════════════════════════════════════════════╣"
	@echo "║ make clean-<agent>     Factory reset worker directory (clean AGENTS.md,  ║"
	@echo "║                        .env, and 'githeri init --agent <agent>')        ║"
	@echo "║                        Supported: hermes, pi, opencode, claude, cursor,  ║"
	@echo "║                                   deepseek, chatgpt, antigravity         ║"
	@echo "║ make clean-all         Factory reset all agent worker directories        ║"
	@echo "║ make update-githeri    Reinstall latest Githeri backend in editable mode ║"
	@echo "║ make status            Inspect active workers, specs, and builds         ║"
	@echo "╚══════════════════════════════════════════════════════════════════════════╝"

# ------------------------------------------------------------------------------
# Core Worker Reset Target
# ------------------------------------------------------------------------------
$(CLEAN_TARGETS): clean-%:
	@agent="$*"; \
	worker_dir="$${agent}-worker"; \
	echo -e "\033[1;33m🧹 Cleaning and resetting $${worker_dir} to factory settings...\033[0m"; \
	rm -rf "$${worker_dir}"; \
	mkdir -p "$${worker_dir}"; \
	if [ -f AGENTS.md ]; then \
		cp AGENTS.md "$${worker_dir}/AGENTS.md"; \
		echo "  ✔ Seeded AGENTS.md"; \
	else \
		echo "  ⚠ Warning: root AGENTS.md not found"; \
	fi; \
	if [ -f .env ]; then \
		cp .env "$${worker_dir}/.env"; \
		echo "  ✔ Seeded .env"; \
	fi; \
	echo "  ⚙ Initializing Githeri workspace for $${agent}..."; \
	(cd "$${worker_dir}" && ../$(GITHERI) init --agent "$${agent}" --register) > /dev/null 2>&1 || \
	(cd "$${worker_dir}" && githeri init --agent "$${agent}" --register) > /dev/null 2>&1 || true; \
	echo -e "\033[1;32m✔ Ready: $${worker_dir} initialized for $${agent}.\033[0m"; \
	echo "  Location: ./$${worker_dir}"; \
	echo "  Launch:   cd $${worker_dir} && githeri start $${agent} \"<prompt>\" --fullstack"

$(RESET_TARGETS): reset-%: clean-%
	@:

# ------------------------------------------------------------------------------
# Clean All Workers
# ------------------------------------------------------------------------------
clean-all:
	@for a in $(AGENTS); do \
		$(MAKE) clean-$$a; \
	done
	@echo -e "\033[1;32m✔ All agent workers have been reset to factory defaults.\033[0m"

# ------------------------------------------------------------------------------
# Backend Sync
# ------------------------------------------------------------------------------
update-githeri:
	@echo -e "\033[1;34m📦 Reinstalling Githeri backend into testbed environment (editable)...\033[0m"
	@if [ -d ../ai/githeri ]; then \
		$(PYTHON) -m pip install --force-reinstall --no-deps -e ../ai/githeri/; \
		echo -e "\033[1;32m✔ Githeri backend linked to latest changes.\033[0m"; \
	else \
		echo -e "\033[1;31m✖ Could not locate ../ai/githeri\033[0m"; \
	fi

# ------------------------------------------------------------------------------
# Status Inspector
# ------------------------------------------------------------------------------
status:
	@echo "═══ Githeri Testbed Status ═══"
	@for a in $(AGENTS); do \
		wdir="$${a}-worker"; \
		if [ -d "$$wdir" ]; then \
			specs=$$(find "$$wdir/.githeri/specs" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' '); \
			plans=$$(find "$$wdir/.githeri/plans" -name "*.md" 2>/dev/null | wc -l | tr -d ' '); \
			fe=$$(if [ -d "$$wdir/frontend" ]; then echo "YES"; else echo "NO"; fi); \
			echo -e "  \033[1;32m●\033[0m $$wdir: specs=$$specs, plans=$$plans, frontend=$$fe"; \
		else \
			echo -e "  \033[1;30m○\033[0m $$wdir: (not created)"; \
		fi; \
	done
