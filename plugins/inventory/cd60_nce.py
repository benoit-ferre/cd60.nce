# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
name: cd60_nce
plugin_type: inventory
short_description: Inventory plugin for iMaster NCE-Campus devices
version_added: "1.0.0"
description:
  - Builds an inventory from /controller/campus/v3/devices. By default, ansible_host is the device name.
options:
  plugin:
    description: Token that ensures this is a source file for the 'cd60_nce' plugin.
    required: true
    choices: ['cd60_nce']
  server_url:
    description: Base URL to the API.
    required: true
    type: string
  token:
    type: string
  username:
    type: string
  password:
    type: string
  validate_certs:
    type: boolean
    default: false
  timeout:
    type: integer
    default: 30
  groups_by:
    description: List of keys to group hosts by (e.g., siteName, type, status)
    type: list
    elements: string
    default: ['siteName', 'type', 'status']
  compose:
    description: Set additional host variables using Jinja2 expressions on the device object
    type: dict
    default: {}
'''

EXAMPLES = r'''
plugin: cd60_nce
server_url: "https://weu.naas.huawei.com:18002"
token: "{{ token }}"
validate_certs: false
groups_by: ['siteName', 'type', 'status']
compose:
  ansible_network_os: "huawei.ce"
'''

from ansible.plugins.inventory import BaseInventoryPlugin
from ..module_utils.client import NceClient
from ..module_utils.helpers import paged_get_devices

class InventoryModule(BaseInventoryPlugin):
    NAME = 'cd60_nce'

    def verify_file(self, path):
        return super(InventoryModule, self).verify_file(path)

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path)

        server_url = self.get_option('server_url')
        token = self.get_option('token')
        username = self.get_option('username')
        password = self.get_option('password')
        validate_certs = self.get_option('validate_certs')
        timeout = self.get_option('timeout')
        groups_by = self.get_option('groups_by') or []
        compose = self.get_option('compose') or {}

        client = NceClient(server_url, token=token, validate_certs=validate_certs, timeout=timeout)
        if not client.token and username and password:
            client.obtain_token(username, password)

        devices = paged_get_devices(client)
        for d in devices:
            name = d.get('name') or d.get('id')
            host_name = name
            self.inventory.add_host(host_name)
            # ansible_host = device name per preference
            self.inventory.set_variable(host_name, 'ansible_host', name)
            # set raw device
            self.inventory.set_variable(host_name, 'nce_device', d)
            # groups
            for k in groups_by:
                gv = d.get(k)
                if gv:
                    gname = f"{k}__{str(gv)}"
                    self.inventory.add_group(gname)
                    self.inventory.add_host(host_name, group=gname)
            # compose (basic variable expansion {{ key }})
            for var, expr in compose.items():
                val = expr
                if isinstance(val, str):
                    for key, v in d.items():
                        val = val.replace('{{ ' + key + ' }}', str(v))
                self.inventory.set_variable(host_name, var, val)
