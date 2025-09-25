
.PHONY: lint integration build
lint:
	ansible-lint || true
integration:
	ANSIBLE_COLLECTIONS_PATHS=./collections ansible-playbook -i tests/integration/inventory tests/integration/site.yml
build:
	ansible-galaxy collection build collections/ansible_collections/cd60/nce -f

BUNDLE_OUT ?= bundle.txt
BUNDLE_SIZE ?= 180k

COLLECTION_ROOT     := $(CURDIR)
INTEG_DIR           := $(COLLECTION_ROOT)/tests/integration
CONFIG_TEMPLATE     := $(INTEG_DIR)/integration_config.yml.template
CONFIG_FILE         := $(INTEG_DIR)/integration_config.yml
CONFIG_SCRIPT       := $(INTEG_DIR)/make_integration_config.sh

TARGETS            ?=
VERBOSITY          ?= -v
DOCKER_IMAGE       ?= ubuntu2204
POST_CLEAN         ?= no

# Couleurs minimes
CINFO  := \033[1;34m
COK    := \033[1;32m
CERR   := \033[1;31m
CEND   := \033[0m

define maybe_post_clean
    if [[ "$(POST_CLEAN)" == "yes" ]]; then \
      $(MAKE) --no-print-directory clean; \
    fi
endef

bundle:
	python3 tools/packaging/pack_collection_with_extractor.py \
	  --root . \
	  -I "plugins/modules/*.py" \
	  -I "plugins/module_utils/*.py" \
	  -I "plugins/lookup/*.py" \
	  -I "plugins/inventory/*.py" \
	  -I "tests/integration/*.yml" \
	  -I "tests/integration/targets/*/tasks/*.yml" \
	  -I "meta/runtime.yml" \
	  -I "docs/cd60.nce-openapi.yml" \
	  -o $(BUNDLE_OUT)

bundle-clean:
	rm -f bundle.txt bundle_part_*.part

config: 
	@echo -e "$(CINFO)[config] Génération du fichier $(CONFIG_FILE)$(CEND)"
	bash "$(CONFIG_SCRIPT)"
	@echo -e "$(COK)[ok] Fichier généré: $(CONFIG_FILE)$(CEND)"

test-local: 
	@echo -e "$(CINFO)[test-local] Exécution ansible-test integration $(VERBOSITY) $(TARGETS)$(CEND)"
	ansible-test integration $(TARGETS) $(VERBOSITY)
	$(call maybe_post_clean)

clean:
	@echo -e "$(CINFO)[clean] Suppression du fichier de config$(CEND)"
	@rm -f "$(CONFIG_FILE)"
	@echo -e "$(COK)[ok] Supprimé: $(CONFIG_FILE)$(CEND)"