# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
lookup: cd60_nce
author: M365 Copilot
version_added: "1.0.0"
short_description: Lookup resources on iMaster NCE-Campus by properties
description:
  - Resolve objects (sites, devices) by specifying filter criteria and return the id, the whole object, or a specific field.
options:
  _terms:
    description:
      - Resource name (e.g., C(sites), C(devices)).
    required: true
  server_url:
    type: str
    required: true
  token:
    type: str
    required: false
  username:
    type: str
    required: false
  password:
    type: str
    required: false
  validate_certs:
    type: bool
    default: false
  where:
    type: dict
    description: Mapping of property->expected value (supports dotted paths).
  unique_by:
    type: list
    elements: str
    description: Additional uniqueness keys to enforce.
  return:
    type: str
    choices: [id, object]
    default: id
'''

EXAMPLES = r'''
- name: Get a site id by name
  set_fact:
    site_id: "{{ lookup('cd60.nce.cd60_nce', 'sites', server_url=server_url, token=token, where={'name': 'Siège'}) }}"

- name: Get full device object by name and site
  set_fact:
    device: "{{ lookup('cd60.nce.cd60_nce', 'devices', server_url=server_url, token=token, where={'name': 'sw-access-01', 'siteName': 'Siège'}, return='object') }}"
'''

RETURN = r'''
- When return=id: the UUID string
- When return=object: the full object dict
'''

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_native
from ..module_utils.client import NceClient
from ..module_utils.helpers import resolve_resource

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleError('Resource name is required (sites or devices)')
        resource = terms[0]
        server_url = kwargs.get('server_url')
        if not server_url:
            raise AnsibleError('server_url is required')
        client = NceClient(server_url, token=kwargs.get('token'), validate_certs=kwargs.get('validate_certs', False), timeout=kwargs.get('timeout', 30))
        if not client.token and kwargs.get('username') and kwargs.get('password'):
            client.obtain_token(kwargs['username'], kwargs['password'])
        where = kwargs.get('where') or {}
        unique_by = kwargs.get('unique_by')
        ret = kwargs.get('return', 'id')
        try:
            obj = resolve_resource(client, resource, where=where, unique_by=unique_by)
        except Exception as e:
            raise AnsibleError(to_native(e))
        if ret == 'object':
            return [obj]
        return [obj.get('id')]
