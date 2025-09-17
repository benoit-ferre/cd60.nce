
.PHONY: lint integration build
lint:
	ansible-lint || true
integration:
	ANSIBLE_COLLECTIONS_PATHS=./collections ansible-playbook -i tests/integration/inventory tests/integration/site.yml
build:
	ansible-galaxy collection build collections/ansible_collections/cd60/nce -f
