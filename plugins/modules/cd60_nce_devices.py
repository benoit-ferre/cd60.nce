# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: cd60_nce_devices
short_description: Query/Create/Modify/Delete devices (batch)
version_added: "1.0.0"
description:
  - Interact with /controller/campus/v3/devices for batch operations.
extends_documentation_fragment:
  - cd60.nce.common
options:
  operation:
    description: Which operation to perform.
    choices: [query, create, modify, delete]
    type: str
    required: true
  token:
    description: Existing token. If omitted, username/password will be used to obtain a token.
    type: str
    no_log: true
  username:
    type: str
  password:
    type: str
    no_log: true
  server_url:
    type: str
    required: true
  validate_certs:
    type: bool
    default: false
  timeout:
    type: int
    default: 30
  request:
    description: Request body for create/modify/delete (shape follows OpenAPI).
    type: dict
  query:
    description: Filters for query (name, siteId, esn, mac, pageNo, pageSize).
    type: dict
author:
  - M365 Copilot
'''

EXAMPLES = r'''
- name: Query devices (page 1)
  cd60.nce.cd60_nce_devices:
    operation: query
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    query:
      pageNo: 1
      pageSize: 20
      name: "sw"

- name: Create devices (batch)
  cd60.nce.cd60_nce_devices:
    operation: create
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    request:
      request:
        devices:
          - name: sw-access-01
            siteId: fbb684c8-0d37-496f-bafa-4b06d5151e2e
            esn: 2102354ABC0W9Q000001
            mgmtIp: 10.10.10.10
            type: Switch
            model: S5735-L24P4X-A1

- name: Delete devices (batch)
  cd60.nce.cd60_nce_devices:
    operation: delete
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    request:
      request:
        deviceIds:
          - 00000000-0000-0000-0000-000000000000
          - 11111111-1111-1111-1111-111111111111

- name: Modify devices (batch)
  cd60.nce.cd60_nce_devices:
    operation: modify
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    request:
      request:
        devices:
          - id: 00000000-0000-0000-0000-000000000000
            name: sw-access-01
'''

RETURN = r'''
changed:
  type: bool
response:
  type: dict
  description: Raw response from API
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.client import NceClient, NceHttpError


def run_module():
    args = dict(
        operation=dict(type='str', required=True, choices=['query', 'create', 'modify', 'delete']),
        server_url=dict(type='str', required=True),
        token=dict(type='str', required=False, no_log=True),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        validate_certs=dict(type='bool', default=False),
        timeout=dict(type='int', default=30),
        request=dict(type='dict', required=False),
        query=dict(type='dict', required=False),
    )
    module = AnsibleModule(argument_spec=args, supports_check_mode=False)

    op = module.params['operation']
    client = NceClient(module.params['server_url'], token=module.params['token'], validate_certs=module.params['validate_certs'], timeout=module.params['timeout'])

    # Obtain token if needed
    if not client.token and module.params.get('username') and module.params.get('password'):
        client.obtain_token(module.params['username'], module.params['password'])

    try:
        if op == 'query':
            params = module.params.get('query') or {}
            resp = client.request('GET', '/controller/campus/v3/devices', params=params)
            module.exit_json(changed=False, response=resp)
        elif op == 'create':
            resp = client.request('POST', '/controller/campus/v3/devices', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
        elif op == 'modify':
            resp = client.request('PUT', '/controller/campus/v3/devices', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
        elif op == 'delete':
            resp = client.request('DELETE', '/controller/campus/v3/devices', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
    except NceHttpError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()

if __name__ == '__main__':
    main()
