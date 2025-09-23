# -*- coding: utf-8 -*-
# (c) 2025 cd60.nce
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function
__metaclass__ = type
DOCUMENTATION = r"""
module: cd60_nce_site
short_description: Manage Huawei iMaster NCE-Campus sites (tenant view)
version_added: "1.0.0"
description:
  - Create, update, or delete a single site on Huawei iMaster NCE-Campus (tenant view).
  - Idempotent: only fields explicitly provided under C(object) are compared/applied.
  - Authentication is performed with a tenant token passed in header C(X-ACCESS-TOKEN).
options:
  token:
    description: Tenant token to authenticate against NCE (X-ACCESS-TOKEN).
    type: str
    required: true
    no_log: true
  base_uri:
    description: Base URI for the NCE API (tenant view), e.g. C(https://weu.naas.huawei.com:18002).
    type: str
    required: true
  validate_certs:
    description: Validate TLS certificates.
    type: bool
    default: false
  selector:
    description:
      - Key→value mapping to uniquely identify the target site.
      - You may include C(name) in selector for RENAME (old name). The new name is C(object.name).
      - Only keys provided are used; keys with C(None) are ignored.
    type: dict
    required: false
    default: {}
  object:
    description:
      - Desired properties of the site. Only keys provided here are enforced.
      - Must include C(name) for ALL operations (present and absent).
      - NOTE: Due to Ansible's argument parsing, unspecified suboptions may appear with C(None).
        The module removes such C(None) keys automatically so they are not sent nor compared.
    type: dict
    required: false
    default: {}
    suboptions:
      name:
        description: Site name (default functional identifier).
        type: str
        required: true
      description:
        description: Free-form description.
        type: str
      address:
        description: Postal address or street address of the site.
        type: str
      city:
        description: City name.
        type: str
      country:
        description: Country name or code.
        type: str
      latitude:
        description: Latitude in decimal degrees.
        type: float
      longitude:
        description: Longitude in decimal degrees.
        type: float
      parentId:
        description: Optional parent site identifier (if hierarchy is supported).
        type: str
      timezone:
        description: Time zone identifier of the site (e.g. C(Europe/Paris)).
        type: str
      tags:
        description: Labels/tags for the site.
        type: list
        elements: str
  state:
    description: Target state of the site.
    type: str
    choices: [present, absent]
    default: present
author:
  - cd60.nce
"""
EXAMPLES = r"""
- name: Ensure site is present (only fields below are compared/applied)
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    validate_certs: false
    selector:
      city: "Beauvais"
    object:
      name: "Site-CD60-Beauvais"
      address: "1 Rue de la Préfecture"
      city: "Beauvais"
      country: "FR"
      timezone: "Europe/Paris"
- name: Remove a site by name
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    object:
      name: "Site-CD60-Beauvais"
    state: absent
"""
RETURN = r"""
changed:
  description: Whether any change was made.
  type: bool
diff:
  description:
    - Before/After structure limited to user-provided keys in C(object).
    - Only changed keys are included.
  type: dict
site:
  description: The resulting site payload returned by NCE (when available).
  type: dict
"""
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cd60.nce.plugins.module_utils.nce_utils import (
    emit_result
)
from ansible_collections.cd60.nce.plugins.module_utils.nce_resource import (
    ensure_idempotent_state
)

API_COLLECTION = "/controller/campus/v3/sites"

# Module-specific request builders (URLs + payloads)

def _make_create_request(collection_path, desired):
    # NCE sites require a batch wrapper even for single create
    return (collection_path, {"sites": [desired]})

def _make_update_request(collection_path, obj_id, payload):
    # Default update path uses /{id}
    if obj_id:
        return (f"{collection_path}/{obj_id}", payload)
    return (collection_path, payload)

def _make_delete_request(collection_path, obj_id):
    # NCE sites deletion on collection with {"ids": [id]}
    return (collection_path, {"ids": [obj_id]})


def run_module():
    argument_spec = dict(
        token=dict(type="str", required=True, no_log=True),
        base_uri=dict(type="str", required=True),
        validate_certs=dict(type="bool", default=False),
        selector=dict(type="dict", default={}),
        object=dict(
            type="dict",
            default={},
            options=dict(
                name=dict(type="str", required=True),
                description=dict(type="str"),
                address=dict(type="str"),
                city=dict(type="str"),
                country=dict(type="str"),
                latitude=dict(type="float"),
                longitude=dict(type="float"),
                parentId=dict(type="str"),
                timezone=dict(type="str"),
                tags=dict(type="list", elements="str"),
            ),
        ),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    state = module.params["state"]
    raw_selector = module.params.get("selector") or {}
    raw_object = module.params.get("object") or {}

    result = ensure_idempotent_state(
        module,
        API_COLLECTION,
        selector=raw_selector,
        desired_object=raw_object,
        state=state,
        id_key='id',
        make_create_request=_make_create_request,
        make_update_request=_make_update_request,
        make_delete_request=_make_delete_request,
        extract_keys=("data","list","sites","items"),
    )
    out = emit_result(module, result, resource_key='site')
    module.exit_json(**out)


def main():
    run_module()

if __name__ == "__main__":
    main()
