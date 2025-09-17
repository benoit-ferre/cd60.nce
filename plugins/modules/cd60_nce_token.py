# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: cd60_nce_token
short_description: Obtain or delete an X-ACCESS-TOKEN for iMaster NCE-Campus
version_added: "1.0.0"
description:
  - Obtain (login) or delete (logout) a token using the Northbound API.
options:
  server_url:
    description: Base URL of the iMaster NCE-Campus Northbound API.
    required: true
    type: str
  username:
    description: Username to obtain a token (tenant view).
    type: str
  password:
    description: Password to obtain a token.
    type: str
    no_log: true
  token:
    description: Existing token to delete (logout).
    type: str
    no_log: true
  state:
    description: Whether to login (obtain) or logout (delete) a token.
    choices: [present, absent]
    default: present
    type: str
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
- name: Obtain token
  cd60.nce.cd60_nce_token:
    server_url: https://weu.naas.huawei.com:18002
    username: "admin@ac.branch"
    password: "Aac@123456"
  register: login

- name: Delete token
  cd60.nce.cd60_nce_token:
    server_url: https://weu.naas.huawei.com:18002
    token: "CA48D152F6B19D84:637C38259E..."
    state: absent
'''

RETURN = r'''
changed:
  type: bool
  description: Whether a change occurred
  returned: always
response:
  description: Raw API response
  returned: always
  type: dict
x_access_token:
  description: Token value when state=present
  returned: when obtained
  type: str
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.client import NceClient, NceHttpError

def run_module():
    args = dict(
        server_url=dict(type='str', required=True),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        token=dict(type='str', required=False, no_log=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        validate_certs=dict(type='bool', default=False),
        timeout=dict(type='int', default=30),
    )
    module = AnsibleModule(argument_spec=args, supports_check_mode=False)

    server_url = module.params['server_url']
    username = module.params['username']
    password = module.params['password']
    token = module.params['token']
    state = module.params['state']

    client = NceClient(server_url, token=None, validate_certs=module.params['validate_certs'], timeout=module.params['timeout'])

    try:
        if state == 'present':
            if not username or not password:
                module.fail_json(msg='username and password are required to obtain token')
            resp = client.obtain_token(username, password)
            module.exit_json(changed=True, response=resp, x_access_token=client.token)
        else:
            if not token:
                module.fail_json(msg='token is required to delete token')
            resp = client.delete_token(token)
            module.exit_json(changed=True, response=resp)
    except NceHttpError as e:
        module.fail_json(msg=str(e))


def main():
    run_module()

if __name__ == '__main__':
    main()
