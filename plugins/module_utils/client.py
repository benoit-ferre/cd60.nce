# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import ssl
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError

class NceHttpError(Exception):
    pass

class NceClient(object):
    def __init__(self, server_url, token=None, validate_certs=False, timeout=30):
        self.base = server_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.ctx = None
        if not validate_certs:
            self.ctx = ssl.create_default_context()
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
        else:
            self.ctx = ssl.create_default_context()

    def _headers(self, extra=None):
        headers = {
            'Accept': 'application/json',
        }
        if self.token:
            headers['X-ACCESS-TOKEN'] = self.token
        if extra:
            headers.update(extra)
        return headers

    def request(self, method, path, params=None, data=None, headers=None):
        url = self.base + path
        if params:
            q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if q:
                url += ('&' if '?' in url else '?') + q
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            headers = self._headers({'Content-Type': 'application/json', **(headers or {})})
        else:
            headers = self._headers(headers or {})
        req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as resp:
                ctype = resp.headers.get('Content-Type', '')
                raw = resp.read()
                if 'application/json' in ctype:
                    return json.loads(raw.decode('utf-8'))
                return {'_raw': raw.decode('utf-8', errors='ignore')}
        except HTTPError as e:
            try:
                msg = e.read().decode('utf-8')
            except Exception:
                msg = str(e)
            raise NceHttpError(f"HTTP {e.code} {e.reason}: {msg}")
        except URLError as e:
            raise NceHttpError(f"URL error: {e.reason}")

    # Auth endpoints
    def obtain_token(self, username, password):
        data = {'userName': username, 'password': password}
        resp = self.request('POST', '/controller/v2/tokens', data=data)
        # token in resp['data']['token_id'] typically
        token = None
        try:
            token = resp['data']['token_id']
        except Exception:
            pass
        self.token = token or self.token
        return resp

    def delete_token(self, token_value):
        data = {'token': token_value}
        return self.request('DELETE', '/controller/v2/tokens', data=data)
