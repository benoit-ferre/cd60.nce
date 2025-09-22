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
      - Do not include C(name) here; C(name) belongs under C(object.name).
      - Only keys provided are used; keys with C(None) are ignored.
    type: dict
    required: false
    default: {}
  object:
    description:
      - Desired properties of the site. Only keys provided here are enforced.
      - Must include C(name) for creation.
      - NOTE: Due to Ansible's argument parsing, unspecified suboptions may appear with C(None).
        The module removes such C(None) keys automatically so they are not sent nor compared.
    type: dict
    required: false
    default: {}
    suboptions:
      name:
        description: Site name (default functional identifier).
        type: str
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
      # e.g. match by a business property (do NOT include name here)
      city: "Beauvais"
    object:
      name: "Site-CD60-Beauvais"
      address: "1 Rue de la Préfecture"
      city: "Beauvais"
      country: "FR"
      timezone: "Europe/Paris"

- name: Re-run with same input (idempotent -> changed=false)
  cd60_nce_site:
    token: "{{ nce_token }}"
    base_uri: "https://weu.naas.huawei.com:18002"
    selector:
      city: "Beauvais"
    object:
      name: "Site-CD60-Beauvais"
      address: "1 Rue de la Préfecture"
      city: "Beauvais"
      country: "FR"
      timezone: "Europe/Paris"

- name: Remove a site by name (fallback when selector empty)
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
    - Subset of fields (within C(object)) that differ from the current state.
    - Only includes fields the user actually provided (after removing implicit Nones).
  type: dict
site:
  description: The resulting site payload returned by NCE (when available).
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cd60.nce.plugins.module_utils.nce_http import (
    get_json, post_json, put_json, delete_json
)
from ansible_collections.cd60.nce.plugins.module_utils.nce_utils import (
    prune_unset, strip_readonly, deep_merge, subset_diff, READONLY_KEYS
)
from ansible_collections.cd60.nce.plugins.module_utils.nce_resource import (
    find_by_selector_or_name
)

API_COLLECTION = "/controller/campus/v3/sites"


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
                name=dict(type="str"),
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
    selector = prune_unset(raw_selector)
    desired = prune_unset(raw_object)
    name = desired.get("name")

    if state == "absent":
        current = find_by_selector_or_name(module, API_COLLECTION, selector, name)
        if not current:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True, site=strip_readonly(current, READONLY_KEYS))
        site_id = current.get("id")
        if site_id:
            delete_json(module, f"{API_COLLECTION}/{site_id}")
        else:
            delete_json(module, API_COLLECTION)  # fallback if API supports delete-by-query
        module.exit_json(changed=True)

    # state == present
    if not name and not selector:
        module.fail_json(msg="At least one of selector or object.name must be provided for state=present.")

    current = find_by_selector_or_name(module, API_COLLECTION, selector, name)
    if not current:
        if not name:
            module.fail_json(msg="object.name is required on creation (no existing site found).")
        if module.check_mode:
            module.exit_json(changed=True, diff={"before": {}, "after": desired})
        created = post_json(module, API_COLLECTION, payload=desired)
        module.exit_json(changed=True, site=strip_readonly(created, READONLY_KEYS))

    # exists -> compute subset diff
    current_stripped = strip_readonly(current, READONLY_KEYS)
    diff_subset = subset_diff(current_stripped, desired)
    if not diff_subset:
        module.exit_json(changed=False, site=current_stripped)

    if module.check_mode:
        module.exit_json(changed=True, diff=diff_subset, site=current_stripped)

    payload = deep_merge(current_stripped, desired)
    site_id = current.get("id")
    if site_id:
        updated = put_json(module, f"{API_COLLECTION}/{site_id}", payload=payload)
    else:
        updated = put_json(module, API_COLLECTION, payload=payload)
    module.exit_json(changed=True, diff=diff_subset, site=strip_readonly(updated, READONLY_KEYS))


def main():
    run_module()

if __name__ == "__main__":
    main()
