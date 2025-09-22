# -*- coding: utf-8 -*-
# Extracted common utilities from nce_site module (cd60.nce)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

# Keys that should never be sent back to the API during updates
READONLY_KEYS = {
    "id", "uuid",
    "createTime", "create_time", "createdAt",
    "updateTime", "update_time", "updatedAt",
}

def prune_unset(value):
    """Remove keys whose value is None (implicit defaults from AnsibleModule).
    Keep empty lists/dicts if they are explicitly present."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if v is None:
                continue
            out[k] = prune_unset(v)
        return out
    if isinstance(value, list):
        return [prune_unset(v) for v in value]
    return value

def strip_readonly(x, readonly_keys=READONLY_KEYS):
    if isinstance(x, dict):
        return {k: strip_readonly(v, readonly_keys) for k, v in x.items() if k not in readonly_keys}
    if isinstance(x, list):
        return [strip_readonly(v, readonly_keys) for v in x]
    return x

def deep_merge(base, overlay):
    """Merge overlay into base recursively (overlay wins), without mutating inputs."""
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

def _deep_copy_for_compare(x):
    if isinstance(x, list):
        return [_deep_copy_for_compare(v) for v in x]
    if isinstance(x, dict):
        return {k: _deep_copy_for_compare(v) for k, v in x.items()}
    return x

def subset_diff(current, desired_subset):
    """Compute differences only for keys explicitly provided by user (desired_subset)."""
    if isinstance(desired_subset, dict):
        diff = {}
        cur = current or {}
        for k, v in desired_subset.items():
            sub = subset_diff(cur.get(k), v)
            if sub is not None:
                diff[k] = sub
        return diff if diff else None
    if isinstance(desired_subset, list):
        return desired_subset if _deep_copy_for_compare(current) != _deep_copy_for_compare(desired_subset) else None
    # scalars
    return desired_subset if current != desired_subset else None
