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
  base_url:
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
    base_url: "https://weu.naas.huawei.com:18002"
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
    base_url: "https://weu.naas.huawei.com:18002"
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
    base_url: "https://weu.naas.huawei.com:18002"
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
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.six.moves.urllib.error import HTTPError

# According to Huawei CloudCampus Java guide, site listing uses /controller/campus/v3/sites?pageIndex=...&pageSize=...
# We keep the collection path here and will always pass pageIndex/pageSize on GET list.
API_COLLECTION = "/controller/campus/v3/sites"

# ------------- Helpers -------------------------------------------------------

READONLY_KEYS = {
    "id", "uuid",
    "createTime", "create_time", "createdAt",
    "updateTime", "update_time", "updatedAt",
}

def _headers(token):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ACCESS-TOKEN": token,
    }

def _prune_unset(value):
    """
    Remove keys whose value is None (implicit defaults from AnsibleModule).
    Keep empty lists/dicts if they are explicitly present.
    """
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if v is None:
                continue
            out[k] = _prune_unset(v)
        return out
    if isinstance(value, list):
        return [_prune_unset(v) for v in value]
    return value

def strip_readonly(x):
    if isinstance(x, dict):
        return {k: strip_readonly(v) for k, v in x.items() if k not in READONLY_KEYS}
    if isinstance(x, list):
        return [strip_readonly(v) for v in x]
    return x

def deep_merge(base, overlay):
    """
    Merge overlay into base recursively (overlay wins), without mutating inputs.
    Useful to avoid overwriting unspecified fields during updates.
    """
    from copy import deepcopy
    if base is None:
        return deepcopy(overlay)
    if overlay is None:
        return deepcopy(base)
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = deepcopy(base)
        for k, v in overlay.items():
            if k in merged:
                merged[k] = deep_merge(merged.get(k), v)
            else:
                merged[k] = deepcopy(v)
        return merged
    # lists & scalars -> overlay wins
    return deepcopy(overlay)

def _normalize_types(x):
    """Conservative normalization for stable comparisons."""
    if isinstance(x, list):
        return [_normalize_types(v) for v in x]
    if isinstance(x, dict):
        return {k: _normalize_types(v) for k, v in x.items()}
    return x

def subset_diff(current, desired_subset):
    """
    Compute differences only for keys explicitly provided by user (desired_subset),
    after pruning implicit Nones.
    """
    if isinstance(desired_subset, dict):
        diff = {}
        cur = current or {}
        for k, v in desired_subset.items():
            sub = subset_diff(cur.get(k), v)
            if sub is not None:
                diff[k] = sub
        return diff if diff else None
    if isinstance(desired_subset, list):
        return desired_subset if _normalize_types(current) != _normalize_types(desired_subset) else None
    # scalars
    return desired_subset if _normalize_types(current) != _normalize_types(desired_subset) else None

# ------------- HTTP primitives ----------------------------------------------

def _get(module, path, query=None):
    url = module.params["base_url"].rstrip("/") + path
    if query:
        url += "?" + urlencode(query)
    resp = open_url(
        url,
        method="GET",
        headers=_headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
    )
    data = resp.read()
    return data and module.from_json(data) or {}

def _post(module, path, payload):
    url = module.params["base_url"].rstrip("/") + path
    resp = open_url(
        url,
        method="POST",
        headers=_headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
        data=module.jsonify(payload),
    )
    data = resp.read()
    return data and module.from_json(data) or {}

def _put(module, path, payload):
    url = module.params["base_url"].rstrip("/") + path
    resp = open_url(
        url,
        method="PUT",
        headers=_headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
        data=module.jsonify(payload),
    )
    data = resp.read()
    return data and module.from_json(data) or {}

def _delete(module, path):
    url = module.params["base_url"].rstrip("/") + path
    try:
        resp = open_url(
            url,
            method="DELETE",
            headers=_headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
        )
        data = resp.read()
        return data and module.from_json(data) or {}
    except HTTPError as exc:
        if getattr(exc, "code", None) == 404:
            return {}
        raise

# ------------- Discovery with strict pagination -----------------------------

def _iter_sites(module, base_filters=None, page_size=100, max_pages=1000):
    """
    Iterate site pages using strict pageIndex/pageSize until exhaustion.
    """
    page_index = 0
    while page_index < max_pages:
        query = {"pageIndex": page_index, "pageSize": page_size}
        if base_filters:
            query.update(base_filters)
        res = _get(module, API_COLLECTION, query=query)
        # Common wrappers: try to extract lists safely
        items = (
            (res.get("data") if isinstance(res, dict) else None)
            or (res.get("list") if isinstance(res, dict) else None)
            or (res.get("sites") if isinstance(res, dict) else None)
            or res
        )
        if isinstance(items, dict):
            items = items.get("list") or items.get("data") or items.get("items") or []
        if not items:
            break
        if not isinstance(items, list):
            items = [items]
        for it in items:
            yield it
        # If fewer than page_size, we're done
        if len(items) < page_size:
            break
        page_index += 1

def _find_site(module, selector, name_fallback, page_size=100):
    """
    Find a site by selector (preferred) or by name (fallback),
    obeying strict pageIndex/pageSize during listing.
    """
    base_filters = {}
    # If selector provided, we don't pass it all as URL filters (not all keys are queryable),
    # we use it to match client-side. However, name fallback can be sent as a server filter.
    if not selector and name_fallback:
        base_filters["name"] = name_fallback

    for it in _iter_sites(module, base_filters=base_filters, page_size=page_size):
        if selector:
            if all(it.get(k) == v for k, v in selector.items()):
                return it
        elif name_fallback and it.get("name") == name_fallback:
            return it
    return None

# ------------- Module logic --------------------------------------------------

def run_module():
    argument_spec = dict(
        token=dict(type="str", required=True, no_log=True),
        base_url=dict(type="str", required=True),
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

    # Neutralize AnsibleModule's implicit None on suboptions
    raw_selector = module.params.get("selector") or {}
    raw_object = module.params.get("object") or {}

    selector = _prune_unset(raw_selector)
    desired = _prune_unset(raw_object)

    name = desired.get("name")

    if state == "absent":
        current = _find_site(module, selector, name)
        if not current:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True, site=strip_readonly(current))
        site_id = current.get("id")
        if site_id:
            _delete(module, f"{API_COLLECTION}/{site_id}")
        else:
            _delete(module, API_COLLECTION)  # fallback if API supports delete-by-query
        module.exit_json(changed=True)

    # state == present
    if not name and not selector:
        module.fail_json(msg="At least one of selector or object.name must be provided for state=present.")

    current = _find_site(module, selector, name)

    if not current:
        # Create with exactly what user asked (subset only)
        if not name:
            module.fail_json(msg="object.name is required on creation (no existing site found).")
        if module.check_mode:
            module.exit_json(changed=True, diff={"before": {}, "after": desired})
        created = _post(module, API_COLLECTION, payload=desired)
        module.exit_json(changed=True, site=strip_readonly(created))

    # Already exists -> compare only the provided subset
    current_stripped = strip_readonly(current)
    diff_subset = subset_diff(current_stripped, desired)

    if not diff_subset:
        module.exit_json(changed=False, site=current_stripped)

    if module.check_mode:
        module.exit_json(changed=True, diff=diff_subset, site=current_stripped)

    # Merge current + desired subset to avoid overwriting unspecified fields
    payload = deep_merge(current_stripped, desired)

    # Prefer PUT /sites/{id} when available
    site_id = current.get("id")
    if site_id:
        updated = _put(module, f"{API_COLLECTION}/{site_id}", payload=payload)
    else:
        updated = _put(module, API_COLLECTION, payload=payload)

    module.exit_json(changed=True, diff=diff_subset, site=strip_readonly(updated))

def main():
    run_module()

if __name__ == "__main__":
    main()
