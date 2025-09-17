# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

class ModuleDocFragment(object):
    DOCUMENTATION = r'''
    options:
      server_url:
        description: Base URL of the iMaster NCE-Campus Northbound API (e.g., https://weu.naas.huawei.com:18002)
        type: str
        required: true
      username:
        description: Username for token acquisition (tenant view). Mutually exclusive with token.
        type: str
      password:
        description: Password for token acquisition. Required when username is provided.
        type: str
        no_log: true
      token:
        description: Existing X-ACCESS-TOKEN value. If not provided and username/password are given, a token will be obtained.
        type: str
        no_log: true
      validate_certs:
        description: Whether to validate TLS certificates.
        type: bool
        default: false
      timeout:
        description: Request timeout, in seconds.
        type: int
        default: 30
    '''
