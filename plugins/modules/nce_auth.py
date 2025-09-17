from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
import json

DOCUMENTATION = r'''
---
module: nce_auth
short_description: Obtain or revoke Huawei NCE X-ACCESS-TOKEN (tenant view)
description:
  - Generates an access token via POST /controller/v2/tokens.
  - Optionally revokes a token via DELETE /controller/v2/tokens.
options:
  base_uri:
    type: str
    default: https://weu.naas.huawei.com:18002
  validate_certs:
    type: bool
    default: false
  username:
    type: str
  password:
    type: str
    no_log: true
  token:
    type: str
  state:
    type: str
    choices: [present, absent]
    default: present
'''

EXAMPLES = r'''
- name: Obtain a token
  cd60.nce.nce_auth:
    username: "admin@ac.branch"
    password: "Aac@123456"
    validate_certs: false
  register: nce_auth

- name: Revoke a token
  cd60.nce.nce_auth:
    token: "{{ nce_auth.token }}"
    state: absent
'''

RETURN = r'''
changed:
  type: bool
  returned: always
token:
  type: str
  returned: when state=present
'''

def main():
    m = AnsibleModule(argument_spec=dict(
        base_uri=dict(type='str', default='https://weu.naas.huawei.com:18002'),
        validate_certs=dict(type='bool', default=False),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        token=dict(type='str', required=False),
        state=dict(type='str', choices=['present','absent'], default='present'),
    ), supports_check_mode=False)
    base_uri=m.params['base_uri'].rstrip('/')
    if m.params['state']=='present':
        if not m.params['username'] or not m.params['password']:
            m.fail_json(msg='username and password are required to obtain a token')
        url=base_uri+'/controller/v2/tokens'
        payload={'userName': m.params['username'], 'password': m.params['password']}
        hdr={'Accept':'application/json','Content-Type':'application/json','Accept-Language':'en-US'}
        try:
            r=open_url(url, method='POST', headers=hdr, data=json.dumps(payload).encode('utf-8'), validate_certs=m.params['validate_certs'], follow_redirects=True)
            data=json.loads(r.read())
        except Exception as e:
            m.fail_json(msg='Failed to obtain token: %s' % e)
        token=None
        if isinstance(data, dict):
            if isinstance(data.get('data'), dict) and 'token_id' in data['data']:
                token=data['data']['token_id']
            elif 'token_id' in data:
                token=data['token_id']
        if not token:
            m.fail_json(msg='Token not found in response', response=data)
        m.exit_json(changed=True, token=token, response=data)
    else:
        token=m.params['token']
        if not token:
            m.fail_json(msg='token is required to revoke')
        url=base_uri+'/controller/v2/tokens'
        payload={'token': token}
        hdr={'Accept':'application/json','Content-Type':'application/json','Accept-Language':'en-US'}
        try:
            r=open_url(url, method='DELETE', headers=hdr, data=json.dumps(payload).encode('utf-8'), validate_certs=m.params['validate_certs'], follow_redirects=True)
            try:
                data=json.loads(r.read())
            except Exception:
                data={}
        except Exception as e:
            m.fail_json(msg='Failed to revoke token: %s' % e)
        m.exit_json(changed=True, response=data)

if __name__=='__main__':
    main()
