# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: cd60_nce_sites
short_description: Query/Create/Modify/Delete sites (batch)
version_added: "1.0.0"
description:
  - Interact with /controller/campus/v3/sites for batch operations.
extends_documentation_fragment:
  - cd60.nce.common
options:
  operation:
    description: Which operation to perform.
    choices: [query, create, modify, delete]
    type: str
    required: true
  token:
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
    description: Request body for create/modify/delete.
    type: dict
  query:
    description: Filters for query (pageIndex, pageSize, name, parentId).
    type: dict
author:
  - M365 Copilot
'''

EXAMPLES = r'''
- name: Query sites
  cd60.nce.cd60_nce_sites:
    operation: query
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    query:
      pageIndex: 0
      pageSize: 20
      name: "Siège"

- name: Create one site
  cd60.nce.cd60_nce_sites:
    operation: create
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    request:
      request:
        sites:
          - name: "Siège"
            address: "1 rue Exemple, 75000 Paris"
            timeZone: "Europe/Paris"
'''

RETURN = r'''
changed:
  type: bool
response:
  type: dict
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

    if not client.token and module.params.get('username') and module.params.get('password'):
        client.obtain_token(module.params['username'], module.params['password'])

    try:
        if op == 'query':
            params = module.params.get('query') or {}
            resp = client.request('GET', '/controller/campus/v3/sites', params=params)
            module.exit_json(changed=False, response=resp)
        elif op == 'create':
            resp = client.request('POST', '/controller/campus/v3/sites', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
        elif op == 'modify':
            resp = client.request('PUT', '/controller/campus/v3/sites', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
        elif op == 'delete':
            resp = client.request('DELETE', '/controller/campus/v3/sites', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
    except NceHttpError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()

if __name__ == '__main__':
    main()
