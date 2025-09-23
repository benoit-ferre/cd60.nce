# -*- coding: utf-8 -*-
# HTTP helpers (cd60.nce)
from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError

def headers(token):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ACCESS-TOKEN": token,
    }

def _build_url(module, path, params=None):
    url = module.params["base_uri"].rstrip('/') + path
    if params:
        q = {k: v for k, v in params.items() if v is not None}
        if q:
            url += '?' + urlencode(q, doseq=True)
    return url

def _parse_json_safely(module, data_bytes):
    if not data_bytes:
        return {}
    try:
        return module.from_json(data_bytes)
    except Exception:
        try:
            return {"raw": data_bytes.decode('utf-8', errors='replace')}
        except Exception:
            return {"raw": str(data_bytes)}

def _fail_from_http_error(module, e, url, method, payload=None):
    body_txt = None
    body_obj = None
    try:
        body_bytes = e.read()
        body_txt = body_bytes.decode('utf-8', errors='replace') if body_bytes else ''
        try:
            body_obj = module.from_json(body_bytes) if body_bytes else None
        except Exception:
            body_obj = None
    except Exception:
        body_txt = None
        body_obj = None
    msg = "%s %s -> HTTP %s" % (method, url, getattr(e, 'code', 'ERR'))
    kwargs = {
        'status': getattr(e, 'code', None),
        'method': method,
        'url': url,
    }
    if body_obj is not None:
        kwargs['response'] = body_obj
        if isinstance(body_obj, dict):
            for k in ('message', 'msg', 'error', 'description', 'desc'):
                if k in body_obj and isinstance(body_obj[k], (str, int)):
                    msg += ": %s" % body_obj[k]
                    break
    elif body_txt:
        kwargs['response_text'] = body_txt
    if payload is not None:
        kwargs['request_payload'] = payload
    module.fail_json(msg=msg, **kwargs)

def get_json(module, path, params=None):
    url = _build_url(module, path, params)
    try:
        resp = open_url(
            url,
            method="GET",
            headers=headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
        )
        data = resp.read()
        return _parse_json_safely(module, data)
    except HTTPError as e:
        _fail_from_http_error(module, e, url, 'GET')
    except URLError as e:
        module.fail_json(msg="GET %s failed: %s" % (url, e))

def post_json(module, path, payload):
    url = _build_url(module, path)
    try:
        resp = open_url(
            url,
            method="POST",
            headers=headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
            data=module.jsonify(payload),
        )
        data = resp.read()
        return _parse_json_safely(module, data)
    except HTTPError as e:
        _fail_from_http_error(module, e, url, 'POST', payload=payload)
    except URLError as e:
        module.fail_json(msg="POST %s failed: %s" % (url, e), request_payload=payload)

def put_json(module, path, payload):
    url = _build_url(module, path)
    try:
        resp = open_url(
            url,
            method="PUT",
            headers=headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
            data=module.jsonify(payload),
        )
        data = resp.read()
        return _parse_json_safely(module, data)
    except HTTPError as e:
        _fail_from_http_error(module, e, url, 'PUT', payload=payload)
    except URLError as e:
        module.fail_json(msg="PUT %s failed: %s" % (url, e), request_payload=payload)

def delete_json(module, path, payload=None):
    url = _build_url(module, path)
    try:
        resp = open_url(
            url,
            method="DELETE",
            headers=headers(module.params["token"]),
            validate_certs=module.params["validate_certs"],
            data=module.jsonify(payload) if payload is not None else None,
        )
        data = resp.read()
        return _parse_json_safely(module, data)
    except HTTPError as e:
        _fail_from_http_error(module, e, url, 'DELETE', payload=payload)
    except URLError as e:
        module.fail_json(msg="DELETE %s failed: %s" % (url, e), request_payload=payload)

def iter_paged(module, path, base_filters=None, page_size=100, max_pages=1000, extract_keys=("data","list","sites","items")):
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
