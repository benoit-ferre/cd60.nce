# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from .client import NceClient, NceHttpError


def paged_get_devices(client, name=None, siteId=None, esn=None, mac=None, page_size=100):
    page_no = 1
    all_devices = []
    while True:
        params = {
            'pageNo': page_no,
            'pageSize': page_size,
            'name': name,
            'siteId': siteId,
            'esn': esn,
            'mac': mac,
        }
        resp = client.request('GET', '/controller/campus/v3/devices', params=params)
        data = resp.get('data', {})
        pagination = data.get('pagination', {})
        devices = data.get('devices', [])
        all_devices.extend(devices)
        total = pagination.get('totalSize', len(all_devices))
        if len(all_devices) >= total or not devices:
            break
        page_no += 1
    return all_devices


def paged_get_sites(client, name=None, parentId=None, page_size=200):
    page_index = 0
    all_sites = []
    while True:
        params = {
            'pageIndex': page_index,
            'pageSize': page_size,
            'name': name,
            'parentId': parentId,
        }
        resp = client.request('GET', '/controller/campus/v3/sites', params=params)
        sites = resp.get('sites')
        if sites is None:
            data = resp
            # normalize possible shapes
            sites = data.get('sites', [])
            total = data.get('totalRecords', len(sites))
        else:
            total = resp.get('totalRecords', len(sites))
        all_sites.extend(sites)
        if len(all_sites) >= total or not sites:
            break
        page_index += 1
    return all_sites


def resolve_unique(objects, where=None, unique_by=None):
    where = where or {}
    def match(o):
        for k, v in where.items():
            ov = o
            for part in k.split('.'):
                if isinstance(ov, dict) and part in ov:
                    ov = ov[part]
                else:
                    return False
            if str(ov).lower() != str(v).lower():
                return False
        return True
    matches = [o for o in objects if match(o)]
    if unique_by:
        # reduce to unique set according to fields
        keyset = set()
        uniq = []
        for o in matches:
            key = tuple(str(o.get(f)).lower() for f in unique_by)
            if key not in keyset:
                keyset.add(key)
                uniq.append(o)
        matches = uniq
    if len(matches) == 0:
        raise ValueError('No match for resolver criteria')
    if len(matches) > 1:
        raise ValueError('Multiple matches for resolver criteria')
    return matches[0]


def resolve_resource(client, resource, where=None, unique_by=None):
    if resource == 'sites':
        items = paged_get_sites(client)
    elif resource == 'devices':
        items = paged_get_devices(client)
    else:
        raise ValueError('Unsupported resource: %s' % resource)
    return resolve_unique(items, where=where, unique_by=unique_by)
