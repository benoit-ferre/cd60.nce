# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: cd60_nce_device
short_description: Modify/Delete a single device by id
version_added: "1.0.0"
description:
  - Interact with /controller/campus/v3/devices/{id} for single-object operations.
extends_documentation_fragment:
  - cd60.nce.common
options:
  operation:
    description: Operation to perform.
    choices: [modify, delete]
    required: true
    type: str
  id:
    description: Device UUID
    required: true
    type: str
  request:
    description: Request body for modify
    type: dict
  # auth
  server_url:
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
  validate_certs:
    type: bool
    default: false
  timeout:
    type: int
    default: 30
author:
  - M365 Copilot
'''

EXAMPLES = r'''
- name: Rename one device
  cd60.nce.cd60_nce_device:
    operation: modify
    id: 00000000-0000-0000-0000-000000000000
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
    request:
      request:
        name: sw-access-01

- name: Delete one device
  cd60.nce.cd60_nce_device:
    operation: delete
    id: 00000000-0000-0000-0000-000000000000
    server_url: https://weu.naas.huawei.com:18002
    token: "{{ token }}"
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
        operation=dict(type='str', required=True, choices=['modify', 'delete']),
        id=dict(type='str', required=True),
        request=dict(type='dict', required=False),
        server_url=dict(type='str', required=True),
        token=dict(type='str', required=False, no_log=True),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        validate_certs=dict(type='bool', default=False),
        timeout=dict(type='int', default=30),
    )
    module = AnsibleModule(argument_spec=args, supports_check_mode=False)

    op = module.params['operation']
    did = module.params['id']
    client = NceClient(module.params['server_url'], token=module.params['token'], validate_certs=module.params['validate_certs'], timeout=module.params['timeout'])

    if not client.token and module.params.get('username') and module.params.get('password'):
        client.obtain_token(module.params['username'], module.params['password'])

    try:
        if op == 'modify':
            resp = client.request('PUT', f'/controller/campus/v3/devices/{did}', data=module.params.get('request'))
            module.exit_json(changed=True, response=resp)
        else:
            resp = client.request('DELETE', f'/controller/campus/v3/devices/{did}')
            module.exit_json(changed=True, response=resp)
    except NceHttpError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()

if __name__ == '__main__':
    main()
