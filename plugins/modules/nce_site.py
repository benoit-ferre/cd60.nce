
from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text
from ansible_collections.cd60.nce.plugins.module_utils.nce_client import NceClient, NceHttpError

DOCUMENTATION = r'''
---
module: nce_site
short_description: Idempotent management of Huawei NCE Sites (single object)
description:
  - Ensures a site is present (create or update) or absent (delete).
  - Detects create vs update automatically (no explicit operation parameter).
  - Uses business selectors (mapping) for uniqueness; C(name) must be in C(object) but MUST NOT be inside C(selector).
options:
  token:
    description: X-ACCESS-TOKEN returned by nce_auth.
    type: str
    required: true
  base_uri:
    description: Base URI to the NCE API (scheme+host+port).
    type: str
    default: https://weu.naas.huawei.com:18002
  validate_certs:
    description: Whether to validate TLS certificates.
    type: bool
    default: false
  selector:
    description: Mapping of business properties used to locate the site (no 'name').
    type: dict
    required: false
    suboptions:
      id:
        type: str
        description: Optional direct site id when already known.
      organizationName:
        type: str
      address:
        type: str
  object:
    description: Desired site data; MUST include 'name'. All fields configurable.
    type: dict
    required: true
    suboptions:
      name:
        type: str
        required: true
      description:
        type: str
      latitude:
        type: str
      longitude:
        type: str
      longtitude:
        type: str
      contact:
        type: str
      tag:
        type: list
        elements: str
      isolated:
        type: bool
      type:
        type: list
        elements: str
      email:
        type: str
      phone:
        type: str
      postcode:
        type: str
      address:
        type: str
      siteTag:
        type: str
  state:
    description: Target state.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Pagination is respected for GET /controller/campus/v3/sites; parameters pageIndex/pageSize are optional per Huawei docs.
author:
  - Benoit Ferre (@cd60)
'''

EXAMPLES = r'''
- name: Create or update a site
  cd60.nce.nce_site:
    token: "{{ nce_token }}"
    selector:
      organizationName: "Nanjing Research Center"
      address: "66 JiangYun Road"
    object:
      name: "site1"
      type: ["AP"]
      description: "site1"
      latitude: "50"
      longitude: "111"
    state: present

- name: Remove a site
  cd60.nce.nce_site:
    token: "{{ nce_token }}"
    selector:
      organizationName: "Nanjing Research Center"
      address: "66 JiangYun Road"
    object:
      name: "site1"
    state: absent
'''

RETURN = r'''
changed:
  type: bool
  returned: always
site:
  description: The final site object (when available).
  type: dict
  returned: always
'''

ALLOWED_UPDATE_FIELDS=['name','description','latitude','longitude','longtitude','contact','tag','isolated','type','email','phone','postcode','address','siteTag']
CREATE_REQUIRED=['name','type']


def find_site(client, selector, obj):
    selector = selector or {}
    site_id = selector.get('id')
    if site_id:
        data = client.batch_query_sites([site_id]) or {}
        items = data.get('data') or []
        return items[0] if items else None
    name = obj.get('name')
    page = 0
    page_size = 100
    while True:
        resp = client.list_sites(name=name, page_index=page, page_size=page_size)
        items = (resp or {}).get('data') or []
        for it in items:
            if name and to_text(it.get('name','')) != to_text(name):
                continue
            ok = True
            for k, v in (selector or {}).items():
                if k == 'name':
                    continue
                if to_text(it.get(k, '')) != to_text(v):
                    ok = False
                    break
            if ok:
                return it
        if len(items) < page_size:
            break
        page += 1
    return None


def main():
    argspec = dict(
        token=dict(type='str', required=True),
        base_uri=dict(type='str', default='https://weu.naas.huawei.com:18002'),
        validate_certs=dict(type='bool', default=False),
        selector=dict(
            type='dict', required=False, default=None,
            options=dict(
                id=dict(type='str', required=False),
                organizationName=dict(type='str', required=False),
                address=dict(type='str', required=False),
            ),
        ),
        object=dict(
            type='dict', required=True,
            options=dict(
                name=dict(type='str', required=True),
                description=dict(type='str', required=False),
                latitude=dict(type='str', required=False),
                longitude=dict(type='str', required=False),
                longtitude=dict(type='str', required=False),
                contact=dict(type='str', required=False),
                tag=dict(type='list', elements='str', required=False),
                isolated=dict(type='bool', required=False),
                type=dict(type='list', elements='str', required=False),
                email=dict(type='str', required=False),
                phone=dict(type='str', required=False),
                postcode=dict(type='str', required=False),
                address=dict(type='str', required=False),
                siteTag=dict(type='str', required=False),
            ),
        ),
        state=dict(type='str', choices=['present','absent'], default='present'),
        timeout=dict(type='int', default=30),
    )

    module = AnsibleModule(argument_spec=argspec, supports_check_mode=True)

    client=NceClient(module.params['base_uri'], token=module.params['token'], validate_certs=module.params['validate_certs'], timeout=module.params['timeout'])
    selector=module.params['selector']
    obj=module.params['object'] or {}
    if 'name' not in obj:
        module.fail_json(msg='object.name is required')
    if selector and 'name' in selector:
        module.fail_json(msg="Do not include 'name' in selector (use object.name for default identity)")

    try:
        if module.params['state'] == 'present':
            if module.check_mode:
                existing = find_site(client, selector, obj)
                will_change = existing is None
                if not will_change and existing:
                    for k in ALLOWED_UPDATE_FIELDS:
                        if k in obj and existing.get(k) != obj[k]:
                            will_change = True
                            break
                module.exit_json(changed=will_change, site=existing)
            existing = find_site(client, selector, obj)
            if not existing:
                create_obj = {k: v for k, v in obj.items() if k in set(['name','southAccName','type','pattern','longitude','latitude','longtitude','email','phone','postcode','address','siteTag','contact','tag','isolated','description'])}
                missing = [k for k in CREATE_REQUIRED if k not in create_obj]
                if missing:
                    module.fail_json(msg='Missing required fields for creation: ' + ', '.join(missing))
                res = client.create_site(create_obj) or {}
                module.exit_json(changed=True, site=res)
            else:
                site_id = existing.get('id')
                diff = {}
                for k in ALLOWED_UPDATE_FIELDS:
                    if k in obj and existing.get(k) != obj[k]:
                        diff[k] = obj[k]
                if not diff:
                    module.exit_json(changed=False, site=existing)
                client.update_site(site_id, diff)
                module.exit_json(changed=True, site={"id": site_id, **obj}, request=diff)
        else:
            if module.check_mode:
                existing = find_site(client, selector, obj)
                module.exit_json(changed=existing is not None)
            existing = find_site(client, selector, obj)
            if not existing:
                module.exit_json(changed=False)
            client.delete_site(existing.get('id'))
            module.exit_json(changed=True, site=existing)
    except NceHttpError as e:
        module.fail_json(msg='HTTP error', status=e.status, body=e.body)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
