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
  - Authentication uses a tenant token passed in header C(X-ACCESS-TOKEN).
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
    description: Validate TLS certificates (set to false for self-signed).
    type: bool
    default: false
  selector:
    description:
      - Key→value mapping to uniquely identify the target site.
      - You MAY include C(name) in selector for RENAME (old name). The new name is C(object.name).
      - Only provided keys are used; keys with C(None) are ignored.
    type: dict
    required: false
    default: {}
  object:
    description:
      - Desired properties of the site. Only keys provided here are enforced.
      - Must include C(name) for ALL operations (present and absent).
      - For CREATE operations, Huawei API requires C(type) (list[str]); C(southAccName) is optional.
      - The API historically used a misspelled field C(longtitude) alongside C(longitude). This module supports both.
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
        description: Postal/street address.
        type: str
      latitude:
        description: Latitude in decimal degrees (string or number accepted by API).
        type: raw
      longitude:
        description: Longitude in decimal degrees (string or number accepted by API).
        type: raw
      longtitude:
        description: Historical misspelling sometimes used by the API; treated like C(longitude).
        type: raw
      contact:
        description: Contact person for the site.
        type: str
      tag:
        description: Labels/tags for the site.
        type: list
        elements: str
      isolated:
        description: Whether the site is isolated.
        type: bool
      type:
        description:
          - Device role types hosted in this site. REQUIRED on create.
          - Allowed values (Huawei NCE): C(AP), C(AR), C(LSW), C(FW), C(AC), C(ONU), C(OLT), C(TianGuan), C(NE).
          - Note: C(LSW) is the expected value for LAN Switch (do not use "SW").
        type: list
        elements: str
        choices:
          - AP
          - AR
          - LSW
          - FW
          - AC
          - ONU
          - OLT
          - TianGuan
          - NE
      email:
        description: Contact email.
        type: str
      phone:
        description: Contact phone.
        type: str
      postcode:
        description: Postal/ZIP code.
        type: str
      siteTag:
        description: Additional tag field used by NCE.
        type: str
      southAccName:
        description: Southbound access service name (used at create).
        type: str
  state:
    description: Target state of the site.
    type: str
    choices: [present, absent]
    default: present
  ordered_lists:
    description:
      - Optional list of dotted paths inside C(object) which must be treated as ORDERED during idempotence comparison.
      - By default, all lists are UNORDERED (order-insensitive). Use this to make order significant for specific lists.
      - Examples (for this module): C(tag), C(type)
    type: list
    elements: str
author:
  - cd60.nce
"""
EXAMPLES = r""" 
- name: Ensure a site is present (create if missing) with required 'type' for create
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    validate_certs: false
    selector: {} # business keys if needed; don't include "name" except for rename
    object:
      name: "Site-CD60-Beauvais"
      type: ["AP", "LSW"] # REQUIRED on create; allowed: AP, AR, LSW, FW, AC, ONU, OLT, TianGuan, NE
      southAccName: "Public Default South Access"
      address: "1 Rue de la Préfecture"
      latitude: "49.4321"
      longitude: "2.0833"
      contact: "David"
      tag: ["abcd"]
      isolated: false
      email: "ops@example.org"
      phone: "15277431823"
      postcode: "60000"
      siteTag: ""
  register: site_result

- name: Update a site by business selector (renaming from old to new)
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    selector:
      name: "Old-Site-Name" # allowed in selector ONLY for rename
    object:
      name: "New-Site-Name"
      description: "Updated description"
      longtitude: "2.0833" # historical misspelling still accepted by API

- name: Consider 'tag' list as ORDERED (order matters)
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    ordered_lists: ["tag"]          # <---- order is now significant for 'tag'
    object:
      name: "MySite"
      tag: ["alpha", "beta", "gamma"]
"""
RETURN = r""" 
changed:
  description: Whether any change was made.
  type: bool
diff:
  description:
    - Create: { before: {}, after: desired }.
    - Update: { before: <subset of current>, after: <subset of desired> } for the keys you provided.
    - Delete: { before: <FULL current object as returned by API>, after: {} }.
  type: dict
site:
  description: The resulting site payload returned by NCE (readonly fields may be omitted).
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
    # NOTE: Huawei API requires 'type' on create (list[str]); if not provided,
    # the API will return an error (handled centrally in nce_resource).
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
                latitude=dict(type="raw"),
                longitude=dict(type="raw"),
                longtitude=dict(type="raw"),
                contact=dict(type="str"),
                tag=dict(type="list", elements="str"),
                isolated=dict(type="bool"),
                # Validate each item against Huawei's allowed device types for NCE sites
                type=dict(
                    type="list",
                    elements="str",
                    choices=[
                        "AP", "AR", "LSW", "FW", "AC", "ONU", "OLT", "TianGuan", "NE"
                    ],
                ),
                email=dict(type="str"),
                phone=dict(type="str"),
                postcode=dict(type="str"),
                siteTag=dict(type="str"),
                southAccName=dict(type="str"),
            ),
        ),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        ordered_lists=dict(type="list", elements="str", default=[]),
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
        extract_keys=("data", "list", "sites", "items"),
        ordered_list_paths=module.params.get("ordered_lists") or [],
    )
    # emit_result() already exits
    emit_result(module, result, resource_key='site')

def main():
    run_module()
if __name__ == "__main__":
    main()