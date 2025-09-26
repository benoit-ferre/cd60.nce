# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type
import json

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

def _canon_key(obj):
    """
    Build a deterministic sort key for normalized elements (scalars, dicts, lists).
    Uses JSON dumps with sorted keys to be stable across runs.
    """
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return repr(obj)

def _is_list_ordered(path_tuple, ordered_list_paths):
    """
    Decide whether the list at 'path_tuple' should be treated as ordered.
    path_tuple is a tuple of keys from the root of the resource object (e.g. ('interfaces', 'acl', 'rules')).
    ordered_list_paths is an optional iterable of dotted strings like "interfaces.acl.rules".
    """
    if not ordered_list_paths:
        return False
    dotted = ".".join(path_tuple)
    return dotted in set(ordered_list_paths)

def normalize_for_compare(value, ordered_list_paths=None, path=()):
    """
    Recursively normalize a structure for idempotent comparison:
    - dict: normalize each value.
    - list: if path is ordered -> keep order after normalizing children;
            else unordered -> normalize children then sort them by canonical key.
    - scalars: returned as-is.
    """
    if isinstance(value, dict):
        # Keep dicts as dicts but normalize children
        return {k: normalize_for_compare(v, ordered_list_paths, path + (k,)) for k, v in value.items()}
    if isinstance(value, list):
        normalized_items = [normalize_for_compare(v, ordered_list_paths, path) for v in value]
        if _is_list_ordered(path, ordered_list_paths):
            return normalized_items  # order preserved
        # unordered by default -> sort by canonical key
        return sorted(normalized_items, key=_canon_key)
    return value

def subset_diff(current, desired_subset, *, ordered_list_paths=None, path=()):
    """Compute differences only for keys explicitly provided by user (desired_subset).
    Returns a structure of the *desired* values where a difference exists, or None."""
    if isinstance(desired_subset, dict):
        diff = {}
        cur = current or {}
        for k, v in desired_subset.items():
            sub = subset_diff(cur.get(k), v, ordered_list_paths=ordered_list_paths, path=path + (k,))
            if sub is not None:
                diff[k] = sub
        return diff if diff else None
    if isinstance(desired_subset, list):
        cur_norm = normalize_for_compare(current, ordered_list_paths, path)
        des_norm = normalize_for_compare(desired_subset, ordered_list_paths, path)
        return desired_subset if cur_norm != des_norm else None
    # scalars
    return desired_subset if current != desired_subset else None

def build_before_after(current, desired_subset, *, ordered_list_paths=None, path=()):
    """Build a diff structure with explicit 'before' and 'after' restricted to
    keys the user provided in desired_subset, and only for changed values.
    Returns None if no change.
    """
    def _helper(cur, des, pth):
        # returns (before, after) or (None, None) if no change
        if isinstance(des, dict):
            b, a = {}, {}
            any_change = False
            cur = cur or {}
            for k, v in des.items():
                cb, ca = _helper(cur.get(k), v, pth + (k,))
                if cb is not None or ca is not None:
                    b[k] = cb
                    a[k] = ca
                    any_change = True
            if not any_change:
                return (None, None)
            return (b, a)
        if isinstance(des, list):
            cur_norm = normalize_for_compare(cur, ordered_list_paths, pth)
            des_norm = normalize_for_compare(des, ordered_list_paths, pth)
            if cur_norm != des_norm:
                # Show actual before/after values (not normalized) for readability
                return (cur, des)
            return (None, None)
        # scalars
        if cur != des:
            return (cur, des)
        return (None, None)
    before, after = _helper(current, desired_subset, path)
    if before is None and after is None:
        return None
    return {"before": before if before is not None else {}, "after": after if after is not None else {}}

def emit_result(module, result, resource_key, extra=None):
    """Normalize and emit an Ansible module result.
    Keeps only 'changed' and 'diff' from *result* and remaps 'result' -> resource_key.
    - module: AnsibleModule
    - result: dict returned by ensure_idempotent_state()
    - resource_key: name of the top-level key for the sanitized resource (e.g. 'site', 'device')
    - extra: optional dict merged into the output before exit_json
    """
    out = {k: v for k, v in (result or {}).items() if k in ('changed', 'diff')}
    if (result or {}).get('result') is not None:
        out[resource_key] = result['result']
    if extra:
        out.update(extra)
    module.exit_json(**out)
