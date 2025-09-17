.PHONY: build lint test

COLL_TGZ := cd60-nce.tar.gz

build:
	ansible-galaxy collection build . -v

lint:
	ansible-lint || true

test:
	ansible-playbook -i localhost, -c local examples/devices_create.yml --check || true
