# -*- coding: utf-8 -*-
# Resource discovery helpers (generic) extracted from nce_site module
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cd60.nce.plugins.module_utils.nce_http import iter_paged


def find_by_selector_or_name(module, collection_path, selector, name_fallback, page_size=100, extract_keys=("data","list","sites","items")):
    """Find an object by selector (preferred) or by name (fallback), obeying pagination.
    selector: mapping of business keys (MUST NOT include 'name').
    name_fallback: object.name to look up when selector is empty.
    """
    base_filters = {}
    if not selector and name_fallback:
        base_filters["name"] = name_fallback
    for it in iter_paged(module, collection_path, base_filters=base_filters, page_size=page_size, extract_keys=extract_keys):
        if selector:
            if all(it.get(k) == v for k, v in selector.items()):
                return it
        elif name_fallback and it.get("name") == name_fallback:
            return it
    return None

from ansible_collections.cd60.nce.plugins.module_utils.nce_http import (
    get_json, post_json, put_json, delete_json
)
from ansible_collections.cd60.nce.plugins.module_utils.nce_utils import (
    prune_unset, strip_readonly, deep_merge, subset_diff, READONLY_KEYS
)

def ensure_idempotent_state(module,
                             collection_path,
                             selector=None,
                             desired_object=None,
                             state='present',
                             id_key='id',
                             extract_keys=("data","list","sites","items"),
                             page_size=100,
                             readonly_keys=READONLY_KEYS):
    """Generic idempotent state handler for NCE resources.

    - selector: mapping of business keys (must NOT include 'name').
    - desired_object: dict under 'object' (must include 'name' when creating).
    - state: 'present'|'absent'.

    Returns a dict: {changed: bool, diff: dict|None, result: dict|None, current: dict|None}
    """
    selector = prune_unset(selector or {})
    desired = prune_unset(desired_object or {})
    name = desired.get('name')

    current = find_by_selector_or_name(module, collection_path, selector, name,
                                       page_size=page_size, extract_keys=extract_keys)

    if state == 'absent':
        if not current:
            return {"changed": False, "diff": None, "result": None, "current": None}
        if module.check_mode:
            return {"changed": True, "diff": None, "result": strip_readonly(current, readonly_keys), "current": current}
        obj_id = current.get(id_key)
        if obj_id:
            delete_json(module, f"{collection_path}/{obj_id}")
        else:
            delete_json(module, collection_path)
        return {"changed": True, "diff": None, "result": None, "current": current}

    # state == present
    if not name and not selector:
        module.fail_json(msg="At least one of selector or object.name must be provided for state=present.")

    if not current:
        if not name:
            module.fail_json(msg="object.name is required on creation (no existing resource found).")
        if module.check_mode:
            return {"changed": True, "diff": {"before": {}, "after": desired}, "result": None, "current": None}
        created = post_json(module, collection_path, payload=desired)
        return {"changed": True, "diff": {"before": {}, "after": desired}, "result": strip_readonly(created, readonly_keys), "current": None}

    current_stripped = strip_readonly(current, readonly_keys)
    diff_subset = subset_diff(current_stripped, desired)
    if not diff_subset:
        return {"changed": False, "diff": None, "result": current_stripped, "current": current}

    if module.check_mode:
        return {"changed": True, "diff": diff_subset, "result": current_stripped, "current": current}

    payload = deep_merge(current_stripped, desired)
    obj_id = current.get(id_key)
    if obj_id:
        updated = put_json(module, f"{collection_path}/{obj_id}", payload=payload)
    else:
        updated = put_json(module, collection_path, payload=payload)
    return {"changed": True, "diff": diff_subset, "result": strip_readonly(updated, readonly_keys), "current": current}
