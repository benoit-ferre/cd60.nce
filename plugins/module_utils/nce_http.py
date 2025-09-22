# -*- coding: utf-8 -*-
# HTTP helpers extracted from nce_site module (cd60.nce)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.six.moves.urllib.error import HTTPError


def headers(token):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ACCESS-TOKEN": token,
    }


def _build_url(module, path, params=None):
    url = module.params["base_uri"].rstrip('/') + path
    if params:
        # Filter None values
        q = {k: v for k, v in params.items() if v is not None}
        if q:
            url += '?' + urlencode(q)
    return url


def get_json(module, path, params=None):
    url = _build_url(module, path, params)
    resp = open_url(
        url,
        method="GET",
        headers=headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
    )
    data = resp.read()
    return (data and module.from_json(data)) or {}


def post_json(module, path, payload):
    url = _build_url(module, path)
    resp = open_url(
        url,
        method="POST",
        headers=headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
        data=module.jsonify(payload),
    )
    data = resp.read()
    return (data and module.from_json(data)) or {}


def put_json(module, path, payload):
    url = _build_url(module, path)
    resp = open_url(
        url,
        method="PUT",
        headers=headers(module.params["token"]),
        validate_certs=module.params["validate_certs"],
        data=module.jsonify(payload),
    )
    data = resp.read()
    return (data and module.from_json(data)) or {}


def delete_json(module, path):
    url = _build_url(module, path)
    try:
        resp = open_url(
            url,
            method="DELETE",
            headers=headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
        )
        data = resp.read()
        return (data and module.from_json(data)) or {}
    except HTTPError as exc:
        if getattr(exc, "code", None) == 404:
            return {}
        raise


def iter_paged(module, path, base_filters=None, page_size=100, max_pages=1000, extract_keys=("data","list","sites","items")):
    """Iterate pages using strict pageIndex/pageSize until exhaustion.
    Tries common response wrappers: keys in extract_keys.
    """
    page_index = 0
    while page_index < max_pages:
        query = {"pageIndex": page_index, "pageSize": page_size}
        if base_filters:
            query.update(base_filters)
        res = get_json(module, path, params=query)
        items = None
        if isinstance(res, dict):
            for k in extract_keys:
                if k in res and isinstance(res[k], (list, dict)):
                    items = res[k]
                    break
        if items is None:
            items = res
        if isinstance(items, dict):
            # sometimes nested under list/data/items
            items = items.get("list") or items.get("data") or items.get("items") or []
        if not items:
            break
        if not isinstance(items, list):
            items = [items]
        for it in items:
            yield it
        if len(items) < page_size:
            break
        page_index += 1
