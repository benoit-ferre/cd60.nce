from __future__ import absolute_import, division, print_function
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleParserError
from ansible_collections.cd60.nce.plugins.module_utils.nce_client import NceClient

DOCUMENTATION = r'''
---
name: cd60.nce.nce_inventory
plugin_type: inventory
short_description: Build Ansible inventory from Huawei NCE Devices
description:
  - Inventory plugin that discovers devices from Huawei iMaster NCE-Campus (tenant view).
  - Adds each device as a host with C(ansible_host) set to the device name.
  - Attaches the full device object under host var C(nce_device).
options:
  plugin:
    description: Must be set to C(cd60.nce.nce_inventory).
    type: str
    required: true
  base_uri:
    description: Base URI to the NCE API (scheme+host+port).
    type: str
    default: https://weu.naas.huawei.com:18002
  token:
    description: X-ACCESS-TOKEN returned by the nce_auth module.
    type: str
    required: true
  validate_certs:
    description: Whether to validate TLS certificates (self-signed allowed when false).
    type: bool
    default: false
  site_ids:
    description: Optional list of site IDs to filter devices on.
    type: list
    elements: str
    required: false
notes:
  - The inventory filename MUST end with C(nce.yml) or C(nce.yaml) (strict validation).
  - Paginates device listing; pageIndex/pageSize are optional per Huawei docs.
author:
  - Benoit Ferre (@cd60)
'''

EXAMPLES = r'''
# nce.yml
plugin: cd60.nce.nce_inventory
base_uri: https://weu.naas.huawei.com:18002
token: "{{ nce_token }}"
validate_certs: false
# site_ids: ["<optional-site-id>"]
'''

RETURN = r'''
hosts:
  description: List of hosts added to the inventory (device names).
  type: list
  elements: str
  returned: always
hostvars:
  description: Per-host variables set by this plugin.
  type: dict
  returned: always
  contains:
    ansible_host:
      description: Set to the device name.
      type: str
    nce_device:
      description: Raw device object as returned by NCE.
      type: dict
'''

class InventoryModule(BaseInventoryPlugin):
    NAME = 'cd60.nce.nce_inventory'

    def verify_file(self, path):
        valid=super(InventoryModule,self).verify_file(path)
        if not valid:
            return False
        if not (path.endswith('nce.yml') or path.endswith('nce.yaml')):
            raise AnsibleParserError('Inventory path must end with nce.yml or nce.yaml')
        return True

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule,self).parse(inventory, loader, path)
        data=self._read_config_data(path)
        if data.get('plugin')!=self.NAME:
            raise AnsibleParserError('Invalid plugin field: expected %s' % self.NAME)
        base_uri = data.get('base_uri', 'https://weu.naas.huawei.com:18002')
        token = data.get('token')
        if not token:
            raise AnsibleParserError('token is required')
        validate_certs = bool(data.get('validate_certs', False))
        site_ids = data.get('site_ids') or []
        client=NceClient(base_uri, token=token, validate_certs=validate_certs)

        page=0; page_size=200
        while True:
            resp = client.list_devices(page_index=page, page_size=page_size)
            items = (resp or {}).get('data') or []
            for dev in items:
                if site_ids and (dev.get('siteId') not in site_ids):
                    continue
                name = dev.get('name') or dev.get('id')
                if not name:
                    continue
                self.inventory.add_host(name)
                self.inventory.set_variable(name, 'ansible_host', name)
                self.inventory.set_variable(name, 'nce_device', dev)
            if len(items) < page_size:
                break
            page += 1
