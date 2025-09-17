
from __future__ import absolute_import, division, print_function
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
import json

class NceHttpError(Exception):
    def __init__(self, status, body):
        super(NceHttpError, self).__init__('HTTP %s: %s' % (status, body))
        self.status = status
        self.body = body

class NceClient(object):
    def __init__(self, base_uri, token=None, validate_certs=False, timeout=30, headers=None):
        self.base_uri = base_uri.rstrip('/')
        self.validate_certs = validate_certs
        self.timeout = timeout
        self.hdr = {'Accept':'application/json','Accept-Language':'en-US'}
        if headers:
            self.hdr.update(headers)
        if token:
            self.hdr['X-ACCESS-TOKEN'] = token

    def _request(self, method, path, data=None, params=None):
        url = self.base_uri + path
        if params:
            from urllib.parse import urlencode
            q = {k:v for k,v in params.items() if v is not None}
            if q:
                url += '?' + urlencode(q, doseq=True)
        body=None
        headers=dict(self.hdr)
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            headers['Content-Type']='application/json'
        try:
            r = open_url(url, method=method, headers=headers, data=body,
                         validate_certs=self.validate_certs, timeout=self.timeout, follow_redirects=True)
            txt = r.read().decode(r.headers.get_content_charset() or 'utf-8')
            return json.loads(txt) if txt else None
        except HTTPError as e:
            try:
                err = e.read().decode('utf-8')
            except Exception:
                err = str(e)
            raise NceHttpError(e.code, err)
        except URLError as e:
            raise NceHttpError('URL', str(e))

    def get(self, path, params=None):
        return self._request('GET', path, params=params)
    def post(self, path, data=None, params=None):
        return self._request('POST', path, data=data, params=params)
    def put(self, path, data=None, params=None):
        return self._request('PUT', path, data=data, params=params)
    def delete(self, path, data=None, params=None):
        return self._request('DELETE', path, data=data, params=params)

    # Sites
    def list_sites(self, name=None, page_index=None, page_size=None, site_id=None, sort=None):
        p={}
        if name is not None:
            p['name']=name
        if sort is not None:
            p['sort']=sort
        if page_index is not None:
            p['pageIndex']=page_index
        if page_size is not None:
            p['pageSize']=page_size
        if site_id is not None:
            p['id']=site_id
        return self.get('/controller/campus/v3/sites', params=p)

    def batch_query_sites(self, site_ids):
        return self.post('/controller/campus/v3/sites/action/batch-query', data={'siteIds':site_ids})

    def create_site(self, site_obj):
        return self.post('/controller/campus/v3/sites', data={'sites':[site_obj]})

    def update_site(self, site_id, upd):
        return self.put('/controller/campus/v3/sites/' + site_id, data=upd)

    def delete_site(self, site_id):
        return self.delete('/controller/campus/v3/sites', data={'ids':[site_id]})

    # Devices
    def list_devices(self, name=None, page_index=None, page_size=None, device_id=None, sort=None):
        p={}
        if name is not None:
            p['name']=name
        if sort is not None:
            p['sort']=sort
        if page_index is not None:
            p['pageIndex']=page_index
        if page_size is not None:
            p['pageSize']=page_size
        if device_id is not None:
            p['id']=device_id
        return self.get('/controller/campus/v3/devices', params=p)

    def create_device(self, device_obj):
        return self.post('/controller/campus/v3/devices', data={'devices':[device_obj]})

    def update_device(self, device_id, upd):
        return self.put('/controller/campus/v3/devices/' + device_id, data=upd)

    def delete_device(self, device_id):
        return self.delete('/controller/campus/v3/devices', data={'ids':[device_id]})
