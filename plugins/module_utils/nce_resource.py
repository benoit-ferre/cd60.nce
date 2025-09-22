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
