from __future__ import absolute_import, division, print_function
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text
from ansible_collections.cd60.nce.plugins.module_utils.nce_client import NceClient

DOCUMENTATION = r'''
---
name: nce_lookup
plugin_type: lookup
short_description: Lookup Huawei NCE resources (sites, devices) by business identity
description:
  - Query Huawei iMaster NCE-Campus (tenant view) resources and return their objects.
  - Supports C(sites) and C(devices) resources.
  - Identifier defaults to C(name) when not specified.
requirements:
  - cd60.nce collection installed
options:
  _terms:
    description:
      - Positional arguments.
      - term[0] = resource (C(sites)|C(devices))
      - term[1] = identifier (defaults to C(name))
    type: list
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
notes:
  - Respects pagination semantics (pageIndex/pageSize optional per Huawei docs).
  - Selector must NOT include C(name); use the identifier instead.
author:
  - Benoit Ferre (@cd60)
'''

EXAMPLES = r'''
- name: Lookup a site by name
  vars:
    site: "{{ lookup('cd60.nce.nce_lookup', 'sites', 'MySite') | first }}"

- name: Lookup a device by name
  vars:
    dev: "{{ lookup('cd60.nce.nce_lookup', 'devices', 'SW-Edge-01') | first }}"

- name: Lookup a device by id
  vars:
    dev: "{{ lookup('cd60.nce.nce_lookup', 'devices', 'd3f9b5c2-xxxx-xxxx-xxxx-aaaaaaaaaaaa') | first }}"
'''

RETURN = r'''
_raw:
  description: A list with zero or one resource object (if found).
  type: list
  elements: dict
  returned: always
'''

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleError('Usage: lookup("cd60.nce.nce_lookup", resource, identifier)')
        resource=to_text(terms[0])
        identifier=to_text(terms[1]) if len(terms)>1 else 'name'
        base_uri=kwargs.get('base_uri','https://weu.naas.huawei.com:18002')
        token=kwargs.get('token')
        validate_certs=bool(kwargs.get('validate_certs', False))
        if not token:
            raise AnsibleError('token is required')
        client=NceClient(base_uri, token=token, validate_certs=validate_certs)

        if resource=='sites':
            page=0; page_size=100
            while True:
                resp=client.list_sites(name=identifier, page_index=page, page_size=page_size)
                items=(resp or {}).get('data') or []
                for it in items:
                    if it.get('name')==identifier or it.get('id')==identifier:
                        return [it]
                if len(items)<page_size: break
                page+=1
            return []
        if resource=='devices':
            page=0; page_size=100
            while True:
                resp=client.list_devices(name=identifier, page_index=page, page_size=page_size)
                items=(resp or {}).get('data') or []
                for it in items:
                    if it.get('name')==identifier or it.get('id')==identifier:
                        return [it]
                if len(items)<page_size: break
                page+=1
            return []
        raise AnsibleError('Unsupported resource: %s' % resource)
