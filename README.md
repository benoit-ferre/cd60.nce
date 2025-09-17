# cd60.nce — Ansible Collection for Huawei iMaster NCE-Campus (Tenant View)

This collection provides modules, lookup, and inventory plugins to interact with iMaster NCE-Campus Northbound APIs using the **X-ACCESS-TOKEN** header at port **18002**, following the cd60.nce OpenAPI v0.3.4.

## Features
- Token lifecycle (obtain/delete)
- Devices: query, create (batch), modify (batch/one), delete (batch/one)
- Sites: query, create (batch), modify (batch/one), delete (batch/one)
- **Resolver** that lets you specify object properties (e.g., `site.name`) instead of raw IDs, with support for compound uniqueness
- **Lookup plugin** (`cd60_nce`) similar to NetBox `nb_lookup`
- **Inventory plugin** to pull devices; `ansible_host` is set to the device **name** by default

## Quickstart
```bash
ansible-galaxy collection build ansible_collections/cd60/nce
ansible-galaxy collection install cd60-nce-*.tar.gz --force
```

See `examples/` for playbooks.
