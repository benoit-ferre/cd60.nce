
.PHONY: lint integration build
lint:
	ansible-lint || true
integration:
	ANSIBLE_COLLECTIONS_PATHS=./collections ansible-playbook -i tests/integration/inventory tests/integration/site.yml
build:
	ansible-galaxy collection build collections/ansible_collections/cd60/nce -f

BUNDLE_OUT ?= bundle.txt
BUNDLE_SIZE ?= 180k

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

